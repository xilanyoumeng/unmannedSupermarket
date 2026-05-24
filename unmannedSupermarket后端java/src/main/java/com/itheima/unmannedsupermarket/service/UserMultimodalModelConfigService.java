package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.dto.UserMultimodalModelConfigDTO;
import com.itheima.unmannedsupermarket.vo.MultimodalModelRuntimeConfigVO;
import com.itheima.unmannedsupermarket.vo.UserMultimodalModelConfigVO;

public interface UserMultimodalModelConfigService {

    UserMultimodalModelConfigVO getUserConfig(Long userId);

    UserMultimodalModelConfigVO saveUserConfig(Long userId, UserMultimodalModelConfigDTO dto);

    void deleteUserConfig(Long userId);

    MultimodalModelRuntimeConfigVO getRuntimeConfig(Long userId);
}
