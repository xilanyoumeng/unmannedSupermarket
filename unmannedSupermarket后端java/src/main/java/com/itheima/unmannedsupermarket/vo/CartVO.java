package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Accessors(chain = true)
public class CartVO {

    private Long id;
    private Long userId;
    private String name;
    private List<CartItemVO> items;
    private LocalDateTime createTime;
}
