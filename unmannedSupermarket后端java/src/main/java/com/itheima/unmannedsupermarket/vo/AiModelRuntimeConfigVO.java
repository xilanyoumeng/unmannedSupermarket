package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

import java.math.BigDecimal;

@Data
@Accessors(chain = true)
public class AiModelRuntimeConfigVO {

    private Boolean hasUserConfig;

    private String provider;

    private String baseUrl;

    private String model;

    private String apiKey;

    private BigDecimal temperature;

    private Integer maxTokens;

    private BigDecimal topP;
}
