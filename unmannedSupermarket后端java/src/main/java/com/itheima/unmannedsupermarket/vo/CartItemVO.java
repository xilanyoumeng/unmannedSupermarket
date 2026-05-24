package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Accessors(chain = true)
public class CartItemVO {

    private Long id;
    private Long cartId;
    private Long productId;
    private String productName;
    private BigDecimal productPrice;
    private String productImage;
    private Integer quantity;
    private LocalDateTime createTime;
}
