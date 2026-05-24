package com.itheima.unmannedsupermarket.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class CartItemUpdateDTO {

    @NotNull(message = "购物车ID不能为空")
    private Long cartId;

    @NotNull(message = "购物车明细不能为空")
    @Valid
    private List<CartItemUpdateItemDTO> items;

    @Data
    public static class CartItemUpdateItemDTO {

        @NotNull(message = "商品ID不能为空")
        private Long productId;

        @Min(value = 1, message = "数量不能小于1")
        @NotNull(message = "数量不能为空")
        private Integer quantity;
    }
}
