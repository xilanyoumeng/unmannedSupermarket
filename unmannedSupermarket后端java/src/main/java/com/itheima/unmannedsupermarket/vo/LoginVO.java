package com.itheima.unmannedsupermarket.vo;

import lombok.Data;
import lombok.experimental.Accessors;

@Data
@Accessors(chain = true)
public class LoginVO {

    private Long id;
    private String username;
    private String nickname;
    private String phone;
    private String email;
    private String role;
    private Integer elderlyMode;
    private String token;
}
