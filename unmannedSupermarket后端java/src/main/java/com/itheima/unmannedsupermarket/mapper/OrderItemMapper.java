package com.itheima.unmannedsupermarket.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itheima.unmannedsupermarket.entity.OrderItem;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface OrderItemMapper extends BaseMapper<OrderItem> {

    int insertBatch(List<OrderItem> list);
}
