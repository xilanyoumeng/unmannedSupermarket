package com.itheima.unmannedsupermarket.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itheima.unmannedsupermarket.entity.CartItem;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface CartItemMapper extends BaseMapper<CartItem> {

    int insertBatch(List<CartItem> list);
}
