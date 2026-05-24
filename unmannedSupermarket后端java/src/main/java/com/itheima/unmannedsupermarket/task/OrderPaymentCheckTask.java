package com.itheima.unmannedsupermarket.task;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.itheima.unmannedsupermarket.common.RedisUtil;
import com.itheima.unmannedsupermarket.entity.Order;
import com.itheima.unmannedsupermarket.entity.OrderItem;
import com.itheima.unmannedsupermarket.entity.Product;
import com.itheima.unmannedsupermarket.enums.OrderStatus;
import com.itheima.unmannedsupermarket.mapper.OrderItemMapper;
import com.itheima.unmannedsupermarket.mapper.OrderMapper;
import com.itheima.unmannedsupermarket.mapper.ProductMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Slf4j
@Component
public class OrderPaymentCheckTask {

    private static final String DEADLINE_ZSET_KEY = "order:payment:deadline";
    private static final int PAYMENT_TIMEOUT_MINUTES = 15;

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private OrderItemMapper orderItemMapper;

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private RedisUtil redisUtil;

    @Scheduled(fixedRate = 5000)
    @Transactional(rollbackFor = Exception.class)
    public void checkExpiredPaymentOrders() {
        Set<Long> expiredOrderIds = new HashSet<>();
        collectExpiredOrderIdsFromRedis(expiredOrderIds);
        collectExpiredOrderIdsFromDatabase(expiredOrderIds);

        if (expiredOrderIds.isEmpty()) {
            return;
        }

        for (Long orderId : expiredOrderIds) {
            cancelExpiredOrder(orderId);
            removeDeadlineQueueItem(orderId);
        }
    }

    private void collectExpiredOrderIdsFromRedis(Set<Long> expiredOrderIds) {
        try {
            long now = System.currentTimeMillis();
            Set<String> expiredIds = redisUtil.zRangeByScore(DEADLINE_ZSET_KEY, 0, now);
            if (expiredIds == null || expiredIds.isEmpty()) {
                return;
            }
            for (String orderIdStr : expiredIds) {
                try {
                    expiredOrderIds.add(Long.valueOf(orderIdStr));
                } catch (NumberFormatException e) {
                    log.warn("订单超时队列中存在非法订单ID: {}", orderIdStr);
                    redisUtil.zRemove(DEADLINE_ZSET_KEY, orderIdStr);
                }
            }
        } catch (Exception e) {
            log.warn("读取订单超时 Redis 队列失败，将使用数据库兜底扫描: {}", e.getMessage());
        }
    }

    private void collectExpiredOrderIdsFromDatabase(Set<Long> expiredOrderIds) {
        LocalDateTime deadline = LocalDateTime.now().minusMinutes(PAYMENT_TIMEOUT_MINUTES);
        List<Order> overdueOrders = orderMapper.selectList(
                new LambdaQueryWrapper<Order>()
                        .eq(Order::getStatus, OrderStatus.PENDING_PAYMENT.name())
                        .le(Order::getCreateTime, deadline));

        for (Order order : overdueOrders) {
            expiredOrderIds.add(order.getId());
        }
    }

    private void cancelExpiredOrder(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null || !OrderStatus.PENDING_PAYMENT.name().equals(order.getStatus())) {
            return;
        }

        int updated = orderMapper.update(null,
                new LambdaUpdateWrapper<Order>()
                        .eq(Order::getId, orderId)
                        .eq(Order::getStatus, OrderStatus.PENDING_PAYMENT.name())
                        .set(Order::getStatus, OrderStatus.CANCELLED.name())
                        .set(Order::getUpdateTime, LocalDateTime.now()));

        if (updated <= 0) {
            return;
        }

        restoreOrderStock(orderId);
        log.info("订单号 {} 支付超时超过{}分钟，已自动取消并恢复库存",
                order.getOrderNo(), PAYMENT_TIMEOUT_MINUTES);
    }

    private void restoreOrderStock(Long orderId) {
        List<OrderItem> orderItems = orderItemMapper.selectList(
                new LambdaQueryWrapper<OrderItem>().eq(OrderItem::getOrderId, orderId));
        for (OrderItem orderItem : orderItems) {
            Product product = productMapper.selectById(orderItem.getProductId());
            if (product != null) {
                product.setStock(product.getStock() + orderItem.getQuantity());
                productMapper.updateById(product);
            }
        }
    }

    private void removeDeadlineQueueItem(Long orderId) {
        try {
            redisUtil.zRemove(DEADLINE_ZSET_KEY, orderId.toString());
        } catch (Exception e) {
            log.warn("移除订单超时 Redis 队列项失败, orderId={}, error={}", orderId, e.getMessage());
        }
    }
}
