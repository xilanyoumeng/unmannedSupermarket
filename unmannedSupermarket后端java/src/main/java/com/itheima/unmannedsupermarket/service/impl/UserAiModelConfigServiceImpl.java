package com.itheima.unmannedsupermarket.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.itheima.unmannedsupermarket.common.AiModelApiKeyCrypto;
import com.itheima.unmannedsupermarket.dto.UserAiModelConfigDTO;
import com.itheima.unmannedsupermarket.entity.UserAiModelConfig;
import com.itheima.unmannedsupermarket.mapper.UserAiModelConfigMapper;
import com.itheima.unmannedsupermarket.service.UserAiModelConfigService;
import com.itheima.unmannedsupermarket.vo.AiModelRuntimeConfigVO;
import com.itheima.unmannedsupermarket.vo.UserAiModelConfigVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;

@Service
public class UserAiModelConfigServiceImpl implements UserAiModelConfigService {

    private static final BigDecimal DEFAULT_TEMPERATURE = new BigDecimal("0.70");
    private static final BigDecimal DEFAULT_TOP_P = new BigDecimal("0.90");
    private static final int DEFAULT_MAX_TOKENS = 2048;

    @Autowired
    private UserAiModelConfigMapper mapper;

    @Autowired
    private AiModelApiKeyCrypto apiKeyCrypto;

    @Override
    public UserAiModelConfigVO getUserConfig(Long userId) {
        UserAiModelConfig config = findByUserId(userId);
        return config == null ? null : toVO(config);
    }

    @Override
    public UserAiModelConfigVO saveUserConfig(Long userId, UserAiModelConfigDTO dto) {
        validate(dto);

        UserAiModelConfig config = findByUserId(userId);
        boolean isCreate = config == null;
        if (isCreate) {
            config = new UserAiModelConfig();
            config.setUserId(userId);
        }

        config.setProvider(dto.getProvider().trim());
        config.setBaseUrl(dto.getBaseUrl().trim());
        config.setModel(dto.getModel().trim());
        config.setTemperature(dto.getTemperature() != null ? dto.getTemperature() : DEFAULT_TEMPERATURE);
        config.setMaxTokens(dto.getMaxTokens() != null ? dto.getMaxTokens() : DEFAULT_MAX_TOKENS);
        config.setTopP(dto.getTopP() != null ? dto.getTopP() : DEFAULT_TOP_P);
        config.setEnabled(dto.getEnabled() == null || dto.getEnabled() ? 1 : 0);

        if (StringUtils.hasText(dto.getApiKey())) {
            String apiKey = dto.getApiKey().trim();
            config.setApiKeyCiphertext(apiKeyCrypto.encrypt(apiKey));
            config.setApiKeyLast4(last4(apiKey));
        } else if (isCreate || !StringUtils.hasText(config.getApiKeyCiphertext())) {
            throw new RuntimeException("请填写模型API Key");
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
        mapper.delete(new LambdaQueryWrapper<UserAiModelConfig>()
                .eq(UserAiModelConfig::getUserId, userId));
    }

    @Override
    public AiModelRuntimeConfigVO getRuntimeConfig(Long userId) {
        UserAiModelConfig config = findByUserId(userId);
        if (config == null || config.getEnabled() == null || config.getEnabled() != 1) {
            return new AiModelRuntimeConfigVO().setHasUserConfig(false);
        }
        return new AiModelRuntimeConfigVO()
                .setHasUserConfig(true)
                .setProvider(config.getProvider())
                .setBaseUrl(config.getBaseUrl())
                .setModel(config.getModel())
                .setApiKey(apiKeyCrypto.decrypt(config.getApiKeyCiphertext()))
                .setTemperature(config.getTemperature())
                .setMaxTokens(config.getMaxTokens())
                .setTopP(config.getTopP());
    }

    private UserAiModelConfig findByUserId(Long userId) {
        return mapper.selectOne(new LambdaQueryWrapper<UserAiModelConfig>()
                .eq(UserAiModelConfig::getUserId, userId)
                .last("LIMIT 1"));
    }

    private void validate(UserAiModelConfigDTO dto) {
        String baseUrl = dto.getBaseUrl() == null ? "" : dto.getBaseUrl().trim();
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            throw new RuntimeException("模型服务地址必须以 http:// 或 https:// 开头");
        }
    }

    private UserAiModelConfigVO toVO(UserAiModelConfig config) {
        return new UserAiModelConfigVO()
                .setId(config.getId())
                .setProvider(config.getProvider())
                .setBaseUrl(config.getBaseUrl())
                .setModel(config.getModel())
                .setApiKeyMasked(mask(config.getApiKeyLast4()))
                .setTemperature(config.getTemperature())
                .setMaxTokens(config.getMaxTokens())
                .setTopP(config.getTopP())
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
