package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

import java.util.List;

@Data
@Accessors(chain = true)
public class PageResultVO<T> {

    private List<T> records;
    private Long total;
    private Long page;
    private Long pageSize;
}
