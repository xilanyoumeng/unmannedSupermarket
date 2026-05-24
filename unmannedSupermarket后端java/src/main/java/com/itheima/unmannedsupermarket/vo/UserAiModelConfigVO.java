package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Accessors(chain = true)
public class UserAiModelConfigVO {

    private Long id;

    private String provider;

    private String baseUrl;

    private String model;

    private String apiKeyMasked;

    private BigDecimal temperature;

    private Integer maxTokens;

    private BigDecimal topP;

    private Boolean enabled;

    private LocalDateTime updateTime;
}
