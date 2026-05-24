package com.itheima.unmannedsupermarket.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itheima.unmannedsupermarket.entity.Order;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface OrderMapper extends BaseMapper<Order> {
}
