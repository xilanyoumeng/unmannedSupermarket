package com.itheima.unmannedsupermarket.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "oss")
public class OssProperties {

    private String accessKeyId;
    private String accessKeySecret;
    private String bucketName;
    private String endpoint;
}
