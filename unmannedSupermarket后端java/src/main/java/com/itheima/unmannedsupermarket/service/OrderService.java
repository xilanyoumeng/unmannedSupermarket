package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.dto.OrderCreateDTO;
import com.itheima.unmannedsupermarket.vo.OrderVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;

public interface OrderService {

    PageResultVO<OrderVO> getOrderPage(int page, int pageSize);

    PageResultVO<OrderVO> getAllOrderPage(int page, int pageSize);

    PageResultVO<OrderVO> getOrderPageByStatus(int page, int pageSize, String status);

    OrderVO getOrderDetail(Long orderId);

    OrderVO createOrder(OrderCreateDTO dto);

    OrderVO payOrder(Long orderId);

    OrderVO cancelOrder(Long orderId);
}
