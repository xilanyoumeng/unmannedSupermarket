package com.itheima.unmannedsupermarket.config;

import com.itheima.unmannedsupermarket.common.ApiKeyUtil;
import com.itheima.unmannedsupermarket.common.JwtUtil;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Slf4j
@Component
public class LoginInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private ApiKeyUtil apiKeyUtil;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                             Object handler) throws Exception {
        // 1. 优先检查 X-API-Key，供 Python 等第三方服务使用
        String apiKey = request.getHeader("X-API-Key");
        if (apiKey != null && apiKeyUtil.isValid(apiKey)) {
            String userIdHeader = request.getHeader("X-User-Id");
            if (userIdHeader == null) {
                response.setContentType("application/json;charset=UTF-8");
                response.setStatus(400);
                response.getWriter().write("{\"code\":400,\"message\":\"缺少 X-User-Id 头\"}");
                return false;
            }
            Long userId = Long.valueOf(userIdHeader);
            request.setAttribute("userId", userId);
            request.setAttribute("username", "api-caller");
            UserContextHolder.setUserId(userId);
            UserContextHolder.setUsername("api-caller");
            log.debug("API Key 认证通过, userId: {}", userId);
            return true;
        }

        // 2. 否则走 JWT 认证
        String token = request.getHeader("Authorization");

        if (token == null || !token.startsWith("Bearer ")) {
            response.setContentType("application/json;charset=UTF-8");
            response.setStatus(401);
            response.getWriter().write("{\"code\":401,\"message\":\"未登录，请先登录\"}");
            return false;
        }

        token = token.substring(7);

        if (jwtUtil.isTokenExpired(token)) {
            response.setContentType("application/json;charset=UTF-8");
            response.setStatus(401);
            response.getWriter().write("{\"code\":401,\"message\":\"token已过期，请重新登录\"}");
            return false;
        }

        Claims claims = jwtUtil.parseToken(token);
        Long userId = claims.get("userId", Long.class);
        String username = claims.get("username", String.class);

        request.setAttribute("userId", userId);
        request.setAttribute("username", username);

        UserContextHolder.setUserId(userId);
        UserContextHolder.setUsername(username);

        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        UserContextHolder.clear();
    }
}
