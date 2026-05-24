package com.itheima.unmannedsupermarket.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CartItemAddDTO {

    @NotNull(message = "商品ID不能为空")
    private Long productId;

    @Min(value = 1, message = "数量不能小于1")
    @NotNull(message = "数量不能为空")
    private Integer quantity;
}
