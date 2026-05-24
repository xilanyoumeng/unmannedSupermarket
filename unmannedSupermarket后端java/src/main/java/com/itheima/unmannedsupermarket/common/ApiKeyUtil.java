package com.itheima.unmannedsupermarket.common;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ApiKeyUtil {

    @Value("${api.key}")
    private String apiKey;

    public boolean isValid(String key) {
        return apiKey != null && apiKey.equals(key);
    }
}
