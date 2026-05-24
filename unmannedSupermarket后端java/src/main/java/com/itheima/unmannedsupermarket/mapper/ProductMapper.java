package com.itheima.unmannedsupermarket.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itheima.unmannedsupermarket.entity.Product;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ProductMapper extends BaseMapper<Product> {

    @Select("SELECT DISTINCT category FROM product WHERE category IS NOT NULL AND category != '' ORDER BY category")
    List<String> selectDistinctCategories();
}
