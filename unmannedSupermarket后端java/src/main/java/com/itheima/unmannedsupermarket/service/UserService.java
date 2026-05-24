package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.dto.LoginDTO;
import com.itheima.unmannedsupermarket.dto.RegisterDTO;
import com.itheima.unmannedsupermarket.dto.UserInfoUpdateDTO;
import com.itheima.unmannedsupermarket.vo.LoginVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import com.itheima.unmannedsupermarket.vo.UserVO;

public interface UserService {

    LoginVO login(LoginDTO loginDTO);

    UserVO register(RegisterDTO registerDTO);

    UserVO getUserInfo(Long userId);

    UserVO updateUserInfo(Long userId, UserInfoUpdateDTO dto);

    PageResultVO<UserVO> getUserPage(int page, int pageSize);

    void updateElderlyMode(Long userId, Boolean elderlyMode);

    void logout(Long userId);

    void updateUserRole(Long operatorId, Long targetUserId, String role);

    void deleteUser(Long operatorId, Long targetUserId);

    void verifyIdentity(String username, String phone);

    void resetPassword(String username, String phone, String newPassword);

    void resetPasswordByAdmin(Long operatorId, Long targetUserId);
}
