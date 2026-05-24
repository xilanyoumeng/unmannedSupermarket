package com.itheima.unmannedsupermarket.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.itheima.unmannedsupermarket.common.AiModelApiKeyCrypto;
import com.itheima.unmannedsupermarket.dto.UserMultimodalModelConfigDTO;
import com.itheima.unmannedsupermarket.entity.UserMultimodalModelConfig;
import com.itheima.unmannedsupermarket.mapper.UserMultimodalModelConfigMapper;
import com.itheima.unmannedsupermarket.service.UserMultimodalModelConfigService;
import com.itheima.unmannedsupermarket.vo.MultimodalModelRuntimeConfigVO;
import com.itheima.unmannedsupermarket.vo.UserMultimodalModelConfigVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class UserMultimodalModelConfigServiceImpl implements UserMultimodalModelConfigService {

    private static final String DASHSCOPE_PROVIDER = "dashscope";

    @Autowired
    private UserMultimodalModelConfigMapper mapper;

    @Autowired
    private AiModelApiKeyCrypto apiKeyCrypto;

    @Override
    public UserMultimodalModelConfigVO getUserConfig(Long userId) {
        UserMultimodalModelConfig config = findByUserId(userId);
        return config == null ? null : toVO(config);
    }

    @Override
    public UserMultimodalModelConfigVO saveUserConfig(Long userId, UserMultimodalModelConfigDTO dto) {
        UserMultimodalModelConfig config = findByUserId(userId);
        boolean isCreate = config == null;
        if (isCreate) {
            config = new UserMultimodalModelConfig();
            config.setUserId(userId);
            config.setProvider(DASHSCOPE_PROVIDER);
        }

        config.setProvider(DASHSCOPE_PROVIDER);
        config.setEnabled(dto.getEnabled() == null || dto.getEnabled() ? 1 : 0);

        if (StringUtils.hasText(dto.getApiKey())) {
            String apiKey = dto.getApiKey().trim();
            config.setApiKeyCiphertext(apiKeyCrypto.encrypt(apiKey));
            config.setApiKeyLast4(last4(apiKey));
        } else if (isCreate || !StringUtils.hasText(config.getApiKeyCiphertext())) {
            throw new RuntimeException("请填写阿里百炼 DashScope API Key");
        }

        if (isCreate) {
            mapper.insert(config);
        } else {
            mapper.updateById(config);
        }
        return toVO(config);
    }

    @Override
    public void deleteUserConfig(Long userId) {
        mapper.delete(new LambdaQueryWrapper<UserMultimodalModelConfig>()
                .eq(UserMultimodalModelConfig::getUserId, userId));
    }

    @Override
    public MultimodalModelRuntimeConfigVO getRuntimeConfig(Long userId) {
        UserMultimodalModelConfig config = findByUserId(userId);
        if (config == null || config.getEnabled() == null || config.getEnabled() != 1) {
            return new MultimodalModelRuntimeConfigVO().setHasUserConfig(false);
        }
        return new MultimodalModelRuntimeConfigVO()
                .setHasUserConfig(true)
                .setProvider(DASHSCOPE_PROVIDER)
                .setApiKey(apiKeyCrypto.decrypt(config.getApiKeyCiphertext()));
    }

    private UserMultimodalModelConfig findByUserId(Long userId) {
        return mapper.selectOne(new LambdaQueryWrapper<UserMultimodalModelConfig>()
                .eq(UserMultimodalModelConfig::getUserId, userId)
                .last("LIMIT 1"));
    }

    private UserMultimodalModelConfigVO toVO(UserMultimodalModelConfig config) {
        return new UserMultimodalModelConfigVO()
                .setId(config.getId())
                .setProvider(DASHSCOPE_PROVIDER)
                .setApiKeyMasked(mask(config.getApiKeyLast4()))
                .setEnabled(config.getEnabled() != null && config.getEnabled() == 1)
                .setUpdateTime(config.getUpdateTime());
    }

    private String mask(String last4) {
        return StringUtils.hasText(last4) ? "****" + last4 : "";
    }

    private String last4(String apiKey) {
        return apiKey.length() <= 4 ? apiKey : apiKey.substring(apiKey.length() - 4);
    }
}
