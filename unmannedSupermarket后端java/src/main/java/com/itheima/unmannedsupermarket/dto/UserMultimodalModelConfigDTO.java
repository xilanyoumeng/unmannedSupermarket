package com.itheima.unmannedsupermarket.dto;

import lombok.Data;

@Data
public class UserMultimodalModelConfigDTO {

    /**
     * 新增时必填；修改时为空表示继续使用已保存的密钥。
     */
    private String apiKey;

    private Boolean enabled;
}
