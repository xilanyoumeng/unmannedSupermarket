package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import com.itheima.unmannedsupermarket.dto.ElderlyModeDTO;
import com.itheima.unmannedsupermarket.dto.LoginDTO;
import com.itheima.unmannedsupermarket.dto.RegisterDTO;
import com.itheima.unmannedsupermarket.dto.UpdateRoleDTO;
import com.itheima.unmannedsupermarket.dto.UserInfoUpdateDTO;
import com.itheima.unmannedsupermarket.dto.VerifyIdentityDTO;
import com.itheima.unmannedsupermarket.dto.ResetPasswordDTO;
import com.itheima.unmannedsupermarket.service.UserService;
import com.itheima.unmannedsupermarket.vo.LoginVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import com.itheima.unmannedsupermarket.vo.UserVO;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/user")
public class UserController {

    @Autowired
    private UserService userService;

    @PostMapping("/login")
    public Result<LoginVO> login(@Valid @RequestBody LoginDTO loginDTO) {
        log.info("用户登录请求, username: {}", loginDTO.getUsername());
        LoginVO loginVO = userService.login(loginDTO);
        log.info("用户登录成功, userId: {}, username: {}", loginVO.getId(), loginVO.getUsername());
        return Result.success(loginVO);
    }

    @PostMapping("/register")
    public Result<UserVO> register(@Valid @RequestBody RegisterDTO registerDTO) {
        log.info("用户注册请求, username: {}", registerDTO.getUsername());
        UserVO userVO = userService.register(registerDTO);
        log.info("用户注册成功, userId: {}, username: {}", userVO.getId(), userVO.getUsername());
        return Result.success(userVO);
    }

    @GetMapping("/info")
    public Result<UserVO> getUserInfo() {
        Long userId = UserContextHolder.getUserId();
        log.info("查询用户信息, userId: {}", userId);
        UserVO userVO = userService.getUserInfo(userId);
        log.info("用户信息查询成功, userId: {}, username: {}", userVO.getId(), userVO.getUsername());
        return Result.success(userVO);
    }

    @GetMapping("/page")
    public Result<PageResultVO<UserVO>> getUserPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        log.info("分页查询用户列表, page: {}, pageSize: {}", page, pageSize);
        PageResultVO<UserVO> pageResult = userService.getUserPage(page, pageSize);
        return Result.success(pageResult);
    }

    @PutMapping("/info")
    public Result<UserVO> updateUserInfo(@RequestBody UserInfoUpdateDTO dto) {
        Long userId = UserContextHolder.getUserId();
        log.info("修改用户信息, userId: {}", userId);
        UserVO userVO = userService.updateUserInfo(userId, dto);
        log.info("用户信息修改成功, userId: {}", userId);
        return Result.success(userVO);
    }

    @PutMapping("/elderly-mode")
    public Result<Void> updateElderlyMode(@RequestBody ElderlyModeDTO dto) {
        Long userId = UserContextHolder.getUserId();
        log.info("更新适老化模式, userId: {}, elderlyMode: {}", userId, dto.getElderlyMode());
        userService.updateElderlyMode(userId, dto.getElderlyMode());
        log.info("适老化模式更新成功, userId: {}", userId);
        return Result.success();
    }

    @PostMapping("/logout")
    public Result<Void> logout() {
        Long userId = UserContextHolder.getUserId();
        log.info("用户退出登录, userId: {}", userId);
        userService.logout(userId);
        log.info("用户退出登录成功, userId: {}", userId);
        return Result.success();
    }

    @PutMapping("/{userId}/role")
    public Result<Void> updateUserRole(@PathVariable Long userId, @RequestBody UpdateRoleDTO dto) {
        Long operatorId = UserContextHolder.getUserId();
        log.info("修改用户角色, operatorId: {}, targetUserId: {}, role: {}", operatorId, userId, dto.getRole());
        userService.updateUserRole(operatorId, userId, dto.getRole());
        log.info("用户角色修改成功, targetUserId: {}", userId);
        return Result.success();
    }

    @PostMapping("/verify-identity")
    public Result<Void> verifyIdentity(@RequestBody VerifyIdentityDTO dto) {
        log.info("验证身份请求, username: {}", dto.getUsername());
        userService.verifyIdentity(dto.getUsername(), dto.getPhone());
        log.info("身份验证成功, username: {}", dto.getUsername());
        return Result.success();
    }

    @PostMapping("/reset-password")
    public Result<Void> resetPassword(@RequestBody ResetPasswordDTO dto) {
        log.info("重置密码请求, username: {}", dto.getUsername());
        userService.resetPassword(dto.getUsername(), dto.getPhone(), dto.getNewPassword());
        log.info("密码重置成功, username: {}", dto.getUsername());
        return Result.success();
    }

    @PutMapping("/{userId}/reset-password")
    public Result<Void> resetPasswordByAdmin(@PathVariable Long userId) {
        Long operatorId = UserContextHolder.getUserId();
        log.info("管理员重置密码, operatorId: {}, targetUserId: {}", operatorId, userId);
        userService.resetPasswordByAdmin(operatorId, userId);
        log.info("密码重置成功, targetUserId: {}", userId);
        return Result.success();
    }

    @DeleteMapping("/{userId}")
    public Result<Void> deleteUser(@PathVariable Long userId) {
        Long operatorId = UserContextHolder.getUserId();
        log.info("删除用户, operatorId: {}, targetUserId: {}", operatorId, userId);
        userService.deleteUser(operatorId, userId);
        log.info("用户删除成功, targetUserId: {}", userId);
        return Result.success();
    }
}
