package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

@Data
@Accessors(chain = true)
public class MultimodalModelRuntimeConfigVO {

    private Boolean hasUserConfig;

    private String provider;

    private String apiKey;
}
