package com.itheima.unmannedsupermarket.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itheima.unmannedsupermarket.common.JwtUtil;
import com.itheima.unmannedsupermarket.common.RedisUtil;
import com.itheima.unmannedsupermarket.dto.LoginDTO;
import com.itheima.unmannedsupermarket.dto.RegisterDTO;
import com.itheima.unmannedsupermarket.dto.UserInfoUpdateDTO;
import com.itheima.unmannedsupermarket.entity.User;
import com.itheima.unmannedsupermarket.mapper.UserMapper;
import com.itheima.unmannedsupermarket.service.UserService;
import com.itheima.unmannedsupermarket.vo.LoginVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import com.itheima.unmannedsupermarket.vo.UserVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private RedisUtil redisUtil;

    @Override
    public LoginVO login(LoginDTO loginDTO) {
        User user = userMapper.selectOne(
                new LambdaQueryWrapper<User>()
                        .eq(User::getUsername, loginDTO.getUsername()));
        if (user == null) {
            throw new RuntimeException("用户名不存在");
        }
        if (user.getStatus() != null && user.getStatus() == 0) {
            throw new RuntimeException("账号已被禁用");
        }
        String encryptedPassword = DigestUtils.md5DigestAsHex(
                loginDTO.getPassword().getBytes(StandardCharsets.UTF_8));
        if (!Objects.equals(user.getPassword(), encryptedPassword)) {
            throw new RuntimeException("密码错误");
        }
        String token = jwtUtil.generateToken(user.getId(), user.getUsername());

        // 登录后设置 Redis 状态为 true，允许创建新购物车
        redisUtil.set("cart:can_create:" + user.getId(), "true");

        return new LoginVO()
                .setId(user.getId())
                .setUsername(user.getUsername())
                .setNickname(user.getNickname())
                .setPhone(user.getPhone())
                .setEmail(user.getEmail())
                .setRole(user.getRole())
                .setElderlyMode(user.getElderlyMode())
                .setToken(token);
    }

    @Override
    public UserVO register(RegisterDTO registerDTO) {
        if (userMapper.countByUsername(registerDTO.getUsername()) > 0) {
            throw new RuntimeException("用户名已存在");
        }
        if (userMapper.countByPhone(registerDTO.getPhone()) > 0) {
            throw new RuntimeException("手机号已被注册");
        }
        User user = new User();
        user.setUsername(registerDTO.getUsername());
        user.setPassword(DigestUtils.md5DigestAsHex(
                registerDTO.getPassword().getBytes(StandardCharsets.UTF_8)));
        user.setPhone(registerDTO.getPhone());
        user.setEmail(registerDTO.getEmail());
        user.setNickname(registerDTO.getNickname());
        user.setRole("user");
        user.setElderlyMode(0);
        userMapper.insert(user);
        return new UserVO()
                .setId(user.getId())
                .setUsername(user.getUsername());
    }

    @Override
    public UserVO getUserInfo(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        return new UserVO()
                .setId(user.getId())
                .setUsername(user.getUsername())
                .setNickname(user.getNickname())
                .setPhone(user.getPhone())
                .setEmail(user.getEmail())
                .setRole(user.getRole())
                .setStatus(user.getStatus())
                .setElderlyMode(user.getElderlyMode())
                .setCreateTime(user.getCreateTime());
    }

    @Override
    public PageResultVO<UserVO> getUserPage(int page, int pageSize) {
        Page<User> userPage = userMapper.selectPage(new Page<>(page, pageSize), null);
        return new PageResultVO<UserVO>()
                .setRecords(userPage.getRecords().stream().map(user -> new UserVO()
                        .setId(user.getId())
                        .setUsername(user.getUsername())
                        .setNickname(user.getNickname())
                        .setEmail(user.getEmail())
                        .setRole(user.getRole())
                        .setStatus(user.getStatus())
                        .setElderlyMode(user.getElderlyMode())
                        .setCreateTime(user.getCreateTime()))
                        .collect(Collectors.toList()))
                .setTotal(userPage.getTotal())
                .setPage(userPage.getCurrent())
                .setPageSize(userPage.getSize());
    }

    @Override
    public UserVO updateUserInfo(Long userId, UserInfoUpdateDTO dto) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        if (dto.getNickname() != null) {
            user.setNickname(dto.getNickname());
        }
        if (dto.getEmail() != null) {
            user.setEmail(dto.getEmail());
        }
        if (dto.getPhone() != null) {
            user.setPhone(dto.getPhone());
        }
        userMapper.updateById(user);
        return new UserVO()
                .setId(user.getId())
                .setUsername(user.getUsername())
                .setNickname(user.getNickname())
                .setPhone(user.getPhone())
                .setEmail(user.getEmail())
                .setRole(user.getRole())
                .setStatus(user.getStatus())
                .setElderlyMode(user.getElderlyMode())
                .setCreateTime(user.getCreateTime());
    }

    @Override
    public void updateElderlyMode(Long userId, Boolean elderlyMode) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        user.setElderlyMode(elderlyMode != null && elderlyMode ? 1 : 0);
        userMapper.updateById(user);
    }

    @Override
    public void logout(Long userId) {
        // 退出登录后设置 Redis 状态为 false，不允许创建新购物车
        redisUtil.set("cart:can_create:" + userId, "false");
    }

    @Override
    public void updateUserRole(Long operatorId, Long targetUserId, String role) {
        if (operatorId.equals(targetUserId)) {
            throw new RuntimeException("不能修改自己的角色");
        }
        User operator = userMapper.selectById(operatorId);
        if (operator == null) {
            throw new RuntimeException("操作人不存在");
        }
        User targetUser = userMapper.selectById(targetUserId);
        if (targetUser == null) {
            throw new RuntimeException("用户不存在");
        }
        if ("admin".equals(targetUser.getRole()) && !"super_admin".equals(operator.getRole())) {
            throw new RuntimeException("权限不足");
        }
        targetUser.setRole(role);
        userMapper.updateById(targetUser);
    }

    @Override
    public void deleteUser(Long operatorId, Long targetUserId) {
        if (operatorId.equals(targetUserId)) {
            throw new RuntimeException("不能删除自己");
        }
        User operator = userMapper.selectById(operatorId);
        if (operator == null) {
            throw new RuntimeException("操作人不存在");
        }
        User targetUser = userMapper.selectById(targetUserId);
        if (targetUser == null) {
            throw new RuntimeException("用户不存在");
        }
        if ("admin".equals(targetUser.getRole()) && !"super_admin".equals(operator.getRole())) {
            throw new RuntimeException("权限不足");
        }
        userMapper.deleteById(targetUserId);
    }

    @Override
    public void verifyIdentity(String username, String phone) {
        User user = userMapper.selectOne(
                new LambdaQueryWrapper<User>()
                        .eq(User::getUsername, username)
                        .eq(User::getPhone, phone));
        if (user == null) {
            throw new RuntimeException("用户名或手机号不匹配");
        }
    }

    @Override
    public void resetPassword(String username, String phone, String newPassword) {
        User user = userMapper.selectOne(
                new LambdaQueryWrapper<User>()
                        .eq(User::getUsername, username)
                        .eq(User::getPhone, phone));
        if (user == null) {
            throw new RuntimeException("用户不存在或手机号不匹配");
        }
        user.setPassword(DigestUtils.md5DigestAsHex(
                newPassword.getBytes(StandardCharsets.UTF_8)));
        userMapper.updateById(user);
    }

    @Override
    public void resetPasswordByAdmin(Long operatorId, Long targetUserId) {
        User operator = userMapper.selectById(operatorId);
        if (operator == null || !"super_admin".equals(operator.getRole())) {
            throw new RuntimeException("权限不足，仅超级管理员可操作");
        }
        User targetUser = userMapper.selectById(targetUserId);
        if (targetUser == null) {
            throw new RuntimeException("用户不存在");
        }
        targetUser.setPassword(DigestUtils.md5DigestAsHex("123456".getBytes(StandardCharsets.UTF_8)));
        userMapper.updateById(targetUser);
    }

}
