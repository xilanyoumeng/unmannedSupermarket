package com.itheima.unmannedsupermarket.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class UserAiModelConfigDTO {

    @NotBlank(message = "模型厂商不能为空")
    private String provider;

    @NotBlank(message = "模型服务地址不能为空")
    private String baseUrl;

    @NotBlank(message = "模型名称不能为空")
    private String model;

    /**
     * 新增时必填；修改时为空表示继续使用已保存的密钥。
     */
    private String apiKey;

    @DecimalMin(value = "0.0", message = "temperature不能小于0")
    @DecimalMax(value = "2.0", message = "temperature不能大于2")
    private BigDecimal temperature;

    @Min(value = 1, message = "maxTokens不能小于1")
    @Max(value = 200000, message = "maxTokens不能过大")
    private Integer maxTokens;

    @DecimalMin(value = "0.0", message = "topP不能小于0")
    @DecimalMax(value = "1.0", message = "topP不能大于1")
    private BigDecimal topP;

    private Boolean enabled;
}
