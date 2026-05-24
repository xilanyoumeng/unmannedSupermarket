package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

import java.time.LocalDateTime;

@Data
@Accessors(chain = true)
public class UserMultimodalModelConfigVO {

    private Long id;

    private String provider;

    private String apiKeyMasked;

    private Boolean enabled;

    private LocalDateTime updateTime;
}
