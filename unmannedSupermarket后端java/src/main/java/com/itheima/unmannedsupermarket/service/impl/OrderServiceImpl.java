package com.itheima.unmannedsupermarket.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itheima.unmannedsupermarket.common.RedisUtil;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import com.itheima.unmannedsupermarket.dto.OrderCreateDTO;
import com.itheima.unmannedsupermarket.entity.*;
import com.itheima.unmannedsupermarket.enums.OrderStatus;
import com.itheima.unmannedsupermarket.mapper.*;
import com.itheima.unmannedsupermarket.service.OrderService;
import com.itheima.unmannedsupermarket.vo.OrderItemVO;
import com.itheima.unmannedsupermarket.vo.OrderVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
public class OrderServiceImpl implements OrderService {

    private static final long PAYMENT_TIMEOUT_MS = 15 * 60 * 1000L; // 15分钟
    private static final String DEADLINE_ZSET_KEY = "order:payment:deadline";

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private OrderItemMapper orderItemMapper;

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private CartMapper cartMapper;

    @Autowired
    private CartItemMapper cartItemMapper;

    @Autowired
    private RedisUtil redisUtil;

    @Override
    public PageResultVO<OrderVO> getOrderPage(int page, int pageSize) {
        Long userId = UserContextHolder.getUserId();
        Page<Order> orderPage = orderMapper.selectPage(new Page<>(page, pageSize),
                new LambdaQueryWrapper<Order>()
                        .eq(Order::getUserId, userId)
                        .orderByDesc(Order::getCreateTime));

        List<OrderVO> voList = orderPage.getRecords().stream()
                .map(this::buildOrderVO)
                .collect(Collectors.toList());

        return new PageResultVO<OrderVO>()
                .setRecords(voList)
                .setTotal(orderPage.getTotal())
                .setPage(orderPage.getCurrent())
                .setPageSize(orderPage.getSize());
    }

    @Override
    public PageResultVO<OrderVO> getAllOrderPage(int page, int pageSize) {
        Page<Order> orderPage = orderMapper.selectPage(new Page<>(page, pageSize),
                new LambdaQueryWrapper<Order>()
                        .orderByDesc(Order::getCreateTime));

        List<OrderVO> voList = orderPage.getRecords().stream()
                .map(this::buildOrderVO)
                .collect(Collectors.toList());

        return new PageResultVO<OrderVO>()
                .setRecords(voList)
                .setTotal(orderPage.getTotal())
                .setPage(orderPage.getCurrent())
                .setPageSize(orderPage.getSize());
    }

    @Override
    public PageResultVO<OrderVO> getOrderPageByStatus(int page, int pageSize, String status) {
        Page<Order> orderPage = orderMapper.selectPage(new Page<>(page, pageSize),
                new LambdaQueryWrapper<Order>()
                        .eq(Order::getStatus, status)
                        .orderByDesc(Order::getCreateTime));

        List<OrderVO> voList = orderPage.getRecords().stream()
                .map(this::buildOrderVO)
                .collect(Collectors.toList());

        return new PageResultVO<OrderVO>()
                .setRecords(voList)
                .setTotal(orderPage.getTotal())
                .setPage(orderPage.getCurrent())
                .setPageSize(orderPage.getSize());
    }

    @Override
    public OrderVO getOrderDetail(Long orderId) {
        Order order = getOrderWithAuth(orderId);
        return buildOrderVO(order);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public OrderVO createOrder(OrderCreateDTO dto) {
        Long userId = UserContextHolder.getUserId();

        // 清除当前用户的购物车
        clearUserCarts(userId);

        // 查询商品信息
        List<Long> productIds = dto.getItems().stream()
                .map(OrderCreateDTO.OrderItemDTO::getProductId)
                .distinct()
                .collect(Collectors.toList());
        Map<Long, Product> productMap = productMapper.selectBatchIds(productIds).stream()
                .collect(Collectors.toMap(Product::getId, p -> p));

        // 创建订单
        Order order = new Order();
        order.setOrderNo(generateOrderNo());
        order.setUserId(userId);
        order.setStatus(OrderStatus.PENDING_PAYMENT.name());

        BigDecimal totalAmount = BigDecimal.ZERO;
        int totalItems = 0;

        for (OrderCreateDTO.OrderItemDTO item : dto.getItems()) {
            Product product = productMap.get(item.getProductId());
            if (product == null) {
                throw new RuntimeException("商品不存在: " + item.getProductId());
            }
            if (product.getStock() < item.getQuantity()) {
                throw new RuntimeException("商品库存不足: " + product.getName());
            }
            BigDecimal subtotal = product.getPrice().multiply(BigDecimal.valueOf(item.getQuantity()));
            totalAmount = totalAmount.add(subtotal);
            totalItems += item.getQuantity();
        }

        order.setAmount(totalAmount);
        order.setItemsCount(totalItems);
        orderMapper.insert(order);

        // 扣减库存
        for (OrderCreateDTO.OrderItemDTO item : dto.getItems()) {
            Product product = productMap.get(item.getProductId());
            product.setStock(product.getStock() - item.getQuantity());
            productMapper.updateById(product);
        }

        // 创建订单明细
        List<OrderItem> orderItems = dto.getItems().stream().map(item -> {
            Product product = productMap.get(item.getProductId());
            BigDecimal subtotal = product.getPrice().multiply(BigDecimal.valueOf(item.getQuantity()));
            OrderItem orderItem = new OrderItem();
            orderItem.setOrderId(order.getId());
            orderItem.setProductId(item.getProductId());
            orderItem.setProductName(product.getName());
            orderItem.setPrice(product.getPrice());
            orderItem.setQuantity(item.getQuantity());
            orderItem.setSubtotal(subtotal);
            return orderItem;
        }).collect(Collectors.toList());

        orderItemMapper.insertBatch(orderItems);

        // 将订单加入 Redis ZSET 延迟队列，到期时间 = 当前时间 + 15分钟
        long deadline = System.currentTimeMillis() + PAYMENT_TIMEOUT_MS;
        addOrderPaymentDeadline(order.getId(), deadline);

        // 清除用户购物车缓存
        deleteRedisKeyQuietly("cart:can_create:" + userId);

        return buildOrderVO(order, orderItems);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public OrderVO payOrder(Long orderId) {
        Order order = getOrderWithAuth(orderId);

        if (!OrderStatus.PENDING_PAYMENT.name().equals(order.getStatus())) {
            throw new RuntimeException("订单状态不允许支付，当前状态: " + order.getStatus());
        }

        order.setStatus(OrderStatus.PAID.name());
        orderMapper.updateById(order);

        // 热销商品统计：累加商品销量到 Redis ZSET
        List<OrderItem> orderItems = orderItemMapper.selectList(
                new LambdaQueryWrapper<OrderItem>().eq(OrderItem::getOrderId, orderId));
        for (OrderItem orderItem : orderItems) {
            incrementHotProductQuietly(orderItem.getProductId(), orderItem.getQuantity());
        }

        // 支付成功后从延迟队列中移除
        removeOrderPaymentDeadline(orderId);

        return buildOrderVO(order);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public OrderVO cancelOrder(Long orderId) {
        Order order = getOrderWithAuth(orderId);

        if (!OrderStatus.PENDING_PAYMENT.name().equals(order.getStatus())) {
            throw new RuntimeException("订单状态不允许取消，当前状态: " + order.getStatus());
        }

        order.setStatus(OrderStatus.CANCELLED.name());
        orderMapper.updateById(order);

        // 恢复库存
        List<OrderItem> orderItems = orderItemMapper.selectList(
                new LambdaQueryWrapper<OrderItem>().eq(OrderItem::getOrderId, orderId));
        for (OrderItem orderItem : orderItems) {
            Product product = productMapper.selectById(orderItem.getProductId());
            if (product != null) {
                product.setStock(product.getStock() + orderItem.getQuantity());
                productMapper.updateById(product);
            }
        }

        // 从延迟队列中移除
        removeOrderPaymentDeadline(orderId);

        return buildOrderVO(order);
    }

    private void addOrderPaymentDeadline(Long orderId, long deadline) {
        try {
            redisUtil.zAdd(DEADLINE_ZSET_KEY, orderId.toString(), deadline);
        } catch (Exception e) {
            log.warn("写入订单支付超时队列失败，将依赖数据库兜底扫描取消订单, orderId={}, error={}",
                    orderId, e.getMessage());
        }
    }

    private void removeOrderPaymentDeadline(Long orderId) {
        try {
            redisUtil.zRemove(DEADLINE_ZSET_KEY, orderId.toString());
        } catch (Exception e) {
            log.warn("移除订单支付超时队列失败, orderId={}, error={}", orderId, e.getMessage());
        }
    }

    private void deleteRedisKeyQuietly(String key) {
        try {
            redisUtil.delete(key);
        } catch (Exception e) {
            log.warn("删除Redis缓存失败, key={}, error={}", key, e.getMessage());
        }
    }

    private void incrementHotProductQuietly(Long productId, Integer quantity) {
        try {
            redisUtil.zIncrBy("hot:products", productId.toString(), quantity);
        } catch (Exception e) {
            log.warn("更新热销商品统计失败, productId={}, error={}", productId, e.getMessage());
        }
    }

    private String generateOrderNo() {
        String datePart = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        String uuidPart = UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        return datePart + uuidPart;
    }

    private Order getOrderWithAuth(Long orderId) {
        Long userId = UserContextHolder.getUserId();
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new RuntimeException("订单不存在");
        }
        if (!order.getUserId().equals(userId)) {
            throw new RuntimeException("无权操作该订单");
        }
        return order;
    }

    private void clearUserCarts(Long userId) {
        List<Cart> carts = cartMapper.selectList(
                new LambdaQueryWrapper<Cart>().eq(Cart::getUserId, userId));
        if (!carts.isEmpty()) {
            List<Long> cartIds = carts.stream().map(Cart::getId).collect(Collectors.toList());
            cartItemMapper.delete(new LambdaQueryWrapper<CartItem>().in(CartItem::getCartId, cartIds));
            cartMapper.deleteBatchIds(cartIds);
        }
    }

    private OrderVO buildOrderVO(Order order) {
        List<OrderItem> items = orderItemMapper.selectList(
                new LambdaQueryWrapper<OrderItem>().eq(OrderItem::getOrderId, order.getId()));
        return buildOrderVO(order, items);
    }

    private OrderVO buildOrderVO(Order order, List<OrderItem> items) {
        User user = userMapper.selectById(order.getUserId());
        List<OrderItemVO> itemVOs = items.stream()
                .map(this::buildOrderItemVO)
                .collect(Collectors.toList());
        return new OrderVO()
                .setId(order.getId())
                .setOrderNo(order.getOrderNo())
                .setAmount(order.getAmount())
                .setItemsCount(order.getItemsCount())
                .setStatus(OrderStatus.valueOf(order.getStatus()).getDescription())
                .setUsername(user != null ? user.getUsername() : null)
                .setCreatedAt(order.getCreateTime())
                .setItems(itemVOs);
    }

    private OrderItemVO buildOrderItemVO(OrderItem item) {
        return new OrderItemVO()
                .setProductId(item.getProductId())
                .setProductName(item.getProductName())
                .setPrice(item.getPrice())
                .setQuantity(item.getQuantity())
                .setSubtotal(item.getSubtotal());
    }
}
