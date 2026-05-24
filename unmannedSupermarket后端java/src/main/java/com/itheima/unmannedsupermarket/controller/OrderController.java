package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import com.itheima.unmannedsupermarket.dto.OrderCreateDTO;
import com.itheima.unmannedsupermarket.service.OrderService;
import com.itheima.unmannedsupermarket.vo.OrderVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @GetMapping("/page")
    public Result<PageResultVO<OrderVO>> getOrderPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        Long userId = UserContextHolder.getUserId();
        log.info("分页查询订单列表, userId: {}, page: {}, pageSize: {}", userId, page, pageSize);
    PageResultVO<OrderVO> pageResult = orderService.getOrderPage(page, pageSize);
        return Result.success(pageResult);
}

    @GetMapping("/all")
    public Result<PageResultVO<OrderVO>> getAllOrderPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        Long userId = UserContextHolder.getUserId();
        log.info("管理员查询所有订单, userId: {}, page: {}, pageSize: {}", userId, page, pageSize);
        PageResultVO<OrderVO> pageResult = orderService.getAllOrderPage(page, pageSize);
        return Result.success(pageResult);
    }

    @GetMapping("/status")
    public Result<PageResultVO<OrderVO>> getOrderPageByStatus(
            @RequestParam String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        Long userId = UserContextHolder.getUserId();
        log.info("管理员按状态查询订单, userId: {}, status: {}, page: {}, pageSize: {}", userId, status, page, pageSize);
        PageResultVO<OrderVO> pageResult = orderService.getOrderPageByStatus(page, pageSize, status);
        return Result.success(pageResult);
    }

    @GetMapping("/{id}")
    public Result<OrderVO> getOrderDetail(@PathVariable Long id) {
        Long userId = UserContextHolder.getUserId();
        log.info("查询订单详情, userId: {}, orderId: {}", userId, id);
        OrderVO orderVO = orderService.getOrderDetail(id);
        return Result.success(orderVO);
    }

    @PostMapping
    public Result<OrderVO> createOrder(@RequestBody OrderCreateDTO dto) {
        Long userId = UserContextHolder.getUserId();
        log.info("创建订单, userId: {}, itemsCount: {}", userId,
                dto.getItems() != null ? dto.getItems().size() : 0);
        OrderVO orderVO = orderService.createOrder(dto);
        return Result.success(orderVO);
    }

    @PostMapping("/{id}/pay")
    public Result<OrderVO> payOrder(@PathVariable Long id) {
        Long userId = UserContextHolder.getUserId();
        log.info("支付订单, userId: {}, orderId: {}", userId, id);
        OrderVO orderVO = orderService.payOrder(id);
        return Result.success(orderVO);
    }

    @PostMapping("/{id}/cancel")
    public Result<OrderVO> cancelOrder(@PathVariable Long id) {
        Long userId = UserContextHolder.getUserId();
        log.info("取消订单, userId: {}, orderId: {}", userId, id);
        OrderVO orderVO = orderService.cancelOrder(id);
        return Result.success(orderVO);
    }
}
