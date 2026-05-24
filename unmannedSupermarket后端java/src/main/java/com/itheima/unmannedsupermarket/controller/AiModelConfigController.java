package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.ApiKeyUtil;
import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import com.itheima.unmannedsupermarket.dto.UserAiModelConfigDTO;
import com.itheima.unmannedsupermarket.dto.UserMultimodalModelConfigDTO;
import com.itheima.unmannedsupermarket.service.UserAiModelConfigService;
import com.itheima.unmannedsupermarket.service.UserMultimodalModelConfigService;
import com.itheima.unmannedsupermarket.vo.AiModelRuntimeConfigVO;
import com.itheima.unmannedsupermarket.vo.MultimodalModelRuntimeConfigVO;
import com.itheima.unmannedsupermarket.vo.UserAiModelConfigVO;
import com.itheima.unmannedsupermarket.vo.UserMultimodalModelConfigVO;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
public class AiModelConfigController {

    @Autowired
    private UserAiModelConfigService aiModelConfigService;

    @Autowired
    private UserMultimodalModelConfigService multimodalModelConfigService;

    @Autowired
    private ApiKeyUtil apiKeyUtil;

    @GetMapping("/api/user/ai-model")
    public Result<UserAiModelConfigVO> getUserAiModelConfig() {
        Long userId = UserContextHolder.getUserId();
        log.info("查询用户AI模型配置, userId: {}", userId);
        return Result.success(aiModelConfigService.getUserConfig(userId));
    }

    @PutMapping("/api/user/ai-model")
    public Result<UserAiModelConfigVO> saveUserAiModelConfig(@Valid @RequestBody UserAiModelConfigDTO dto) {
        Long userId = UserContextHolder.getUserId();
        log.info("保存用户AI模型配置, userId: {}, provider: {}, model: {}",
                userId, dto.getProvider(), dto.getModel());
        return Result.success(aiModelConfigService.saveUserConfig(userId, dto));
    }

    @DeleteMapping("/api/user/ai-model")
    public Result<Void> deleteUserAiModelConfig() {
        Long userId = UserContextHolder.getUserId();
        log.info("删除用户AI模型配置, userId: {}", userId);
        aiModelConfigService.deleteUserConfig(userId);
        return Result.success();
    }

    @GetMapping("/api/user/multimodal-model")
    public Result<UserMultimodalModelConfigVO> getUserMultimodalModelConfig() {
        Long userId = UserContextHolder.getUserId();
        log.info("查询用户多模态模型配置, userId: {}", userId);
        return Result.success(multimodalModelConfigService.getUserConfig(userId));
    }

    @PutMapping("/api/user/multimodal-model")
    public Result<UserMultimodalModelConfigVO> saveUserMultimodalModelConfig(
            @RequestBody UserMultimodalModelConfigDTO dto) {
        Long userId = UserContextHolder.getUserId();
        log.info("保存用户多模态模型配置, userId: {}", userId);
        return Result.success(multimodalModelConfigService.saveUserConfig(userId, dto));
    }

    @DeleteMapping("/api/user/multimodal-model")
    public Result<Void> deleteUserMultimodalModelConfig() {
        Long userId = UserContextHolder.getUserId();
        log.info("删除用户多模态模型配置, userId: {}", userId);
        multimodalModelConfigService.deleteUserConfig(userId);
        return Result.success();
    }

    @GetMapping("/api/internal/ai-model/current")
    public Result<AiModelRuntimeConfigVO> getRuntimeAiModelConfig(HttpServletRequest request) {
        String apiKey = request.getHeader("X-API-Key");
        if (!apiKeyUtil.isValid(apiKey)) {
            throw new RuntimeException("Only internal service can read AI runtime config");
        }
        Long userId = UserContextHolder.getUserId();
        log.info("Python服务读取用户AI运行时配置, userId: {}", userId);
        return Result.success(aiModelConfigService.getRuntimeConfig(userId));
    }

    @GetMapping("/api/internal/multimodal-model/current")
    public Result<MultimodalModelRuntimeConfigVO> getRuntimeMultimodalModelConfig(HttpServletRequest request) {
        String apiKey = request.getHeader("X-API-Key");
        if (!apiKeyUtil.isValid(apiKey)) {
            throw new RuntimeException("Only internal service can read multimodal runtime config");
        }
        Long userId = UserContextHolder.getUserId();
        log.info("Python服务读取用户多模态运行时配置, userId: {}", userId);
        return Result.success(multimodalModelConfigService.getRuntimeConfig(userId));
    }
}
