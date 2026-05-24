package com.itheima.unmannedsupermarket.vo;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public class OrderVO {

    private Long id;
    private String orderNo;
    private BigDecimal amount;
    private Integer itemsCount;
    private String status;
    private String username;
    private LocalDateTime createdAt;
    private List<OrderItemVO> items;

    public Long getId() {
        return id;
    }

    public OrderVO setId(Long id) {
        this.id = id;
        return this;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public OrderVO setOrderNo(String orderNo) {
        this.orderNo = orderNo;
        return this;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public OrderVO setAmount(BigDecimal amount) {
        this.amount = amount;
        return this;
    }

    public Integer getItemsCount() {
        return itemsCount;
    }

    public OrderVO setItemsCount(Integer itemsCount) {
        this.itemsCount = itemsCount;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public OrderVO setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getUsername() {
        return username;
    }

    public OrderVO setUsername(String username) {
        this.username = username;
        return this;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public OrderVO setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
        return this;
    }

    public List<OrderItemVO> getItems() {
        return items;
    }

    public OrderVO setItems(List<OrderItemVO> items) {
        this.items = items;
        return this;
    }
}
