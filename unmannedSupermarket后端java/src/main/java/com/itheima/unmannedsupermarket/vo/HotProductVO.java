package com.itheima.unmannedsupermarket.vo;

import com.itheima.unmannedsupermarket.entity.Product;
import lombok.Data;
import lombok.experimental.Accessors;

import java.math.BigDecimal;

@Data
@Accessors(chain = true)
public class HotProductVO {

    private Long id;
    private String name;
    private BigDecimal price;
    private Integer stock;
    private String category;
    private String description;
    private String image;
    private String barcode;
    private Integer status;
    private Integer hotCount;

    public static HotProductVO fromProduct(Product product, Integer hotCount) {
        return new HotProductVO()
                .setId(product.getId())
                .setName(product.getName())
                .setPrice(product.getPrice())
                .setStock(product.getStock())
                .setCategory(product.getCategory())
                .setDescription(product.getDescription())
                .setImage(product.getImage())
                .setBarcode(product.getBarcode())
                .setStatus(product.getStatus())
                .setHotCount(hotCount);
    }
}
