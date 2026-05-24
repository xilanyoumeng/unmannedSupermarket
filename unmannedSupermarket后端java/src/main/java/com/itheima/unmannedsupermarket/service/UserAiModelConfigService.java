package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.dto.UserAiModelConfigDTO;
import com.itheima.unmannedsupermarket.vo.AiModelRuntimeConfigVO;
import com.itheima.unmannedsupermarket.vo.UserAiModelConfigVO;

public interface UserAiModelConfigService {

    UserAiModelConfigVO getUserConfig(Long userId);

    UserAiModelConfigVO saveUserConfig(Long userId, UserAiModelConfigDTO dto);

    void deleteUserConfig(Long userId);

    AiModelRuntimeConfigVO getRuntimeConfig(Long userId);
}
