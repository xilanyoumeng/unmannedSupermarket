package com.itheima.unmannedsupermarket.vo;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public class OrderItemVO {

    private Long productId;
    private String productName;
    private BigDecimal price;
    private Integer quantity;
    private BigDecimal subtotal;

    public Long getProductId() {
        return productId;
    }

    public OrderItemVO setProductId(Long productId) {
        this.productId = productId;
        return this;
    }

    public String getProductName() {
        return productName;
    }

    public OrderItemVO setProductName(String productName) {
        this.productName = productName;
        return this;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public OrderItemVO setPrice(BigDecimal price) {
        this.price = price;
        return this;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public OrderItemVO setQuantity(Integer quantity) {
        this.quantity = quantity;
        return this;
    }

    public BigDecimal getSubtotal() {
        return subtotal;
    }

    public OrderItemVO setSubtotal(BigDecimal subtotal) {
        this.subtotal = subtotal;
        return this;
    }
}
