package com.itheima.unmannedsupermarket.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itheima.unmannedsupermarket.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserMapper extends BaseMapper<User> {

    @Select("SELECT COUNT(*) FROM user WHERE username = #{username}")
    long countByUsername(@Param("username") String username);

    @Select("SELECT COUNT(*) FROM user WHERE phone = #{phone}")
    long countByPhone(@Param("phone") String phone);
}
