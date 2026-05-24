package com.itheima.unmannedsupermarket.enums;

public enum OrderStatus {

    PENDING_PAYMENT("待支付"),
    PAID("已支付"),
    CANCELLED("已取消");

    private final String description;

    OrderStatus(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
