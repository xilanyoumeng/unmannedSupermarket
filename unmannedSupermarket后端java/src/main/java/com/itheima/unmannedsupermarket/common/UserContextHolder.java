package com.itheima.unmannedsupermarket.common;

/**
 * 用户上下文持有者，基于 ThreadLocal 存储当前请求的用户信息。
 * 由 LoginInterceptor 在请求进入时设置，请求结束后清除。
 */
public class UserContextHolder {

    private static final ThreadLocal<Long> USER_ID = new ThreadLocal<>();
    private static final ThreadLocal<String> USERNAME = new ThreadLocal<>();

    public static void setUserId(Long userId) {
        USER_ID.set(userId);
    }

    public static Long getUserId() {
        return USER_ID.get();
    }

    public static void setUsername(String username) {
        USERNAME.set(username);
    }

    public static String getUsername() {
        return USERNAME.get();
    }

    public static void clear() {
        USER_ID.remove();
        USERNAME.remove();
    }
}
