package com.itheima.unmannedsupermarket.common;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Component
public class RedisUtil {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    public void set(String key, String value) {
        stringRedisTemplate.opsForValue().set(key, value);
    }

    public void set(String key, String value, long timeout, TimeUnit unit) {
        stringRedisTemplate.opsForValue().set(key, value, timeout, unit);
    }

    public String get(String key) {
        return stringRedisTemplate.opsForValue().get(key);
    }

    public Boolean delete(String key) {
        return stringRedisTemplate.delete(key);
    }

    public Boolean hasKey(String key) {
        return stringRedisTemplate.hasKey(key);
    }

    public Boolean expire(String key, long timeout, TimeUnit unit) {
        return stringRedisTemplate.expire(key, timeout, unit);
    }

    // ======================== ZSET 操作 ========================

    public Boolean zAdd(String key, String value, double score) {
        return stringRedisTemplate.opsForZSet().add(key, value, score);
    }

    public Set<String> zRangeByScore(String key, double min, double max) {
        return stringRedisTemplate.opsForZSet().rangeByScore(key, min, max);
    }

    public Long zRemove(String key, String... values) {
        return stringRedisTemplate.opsForZSet().remove(key, (Object[]) values);
    }

    public Double zIncrBy(String key, String value, double delta) {
        return stringRedisTemplate.opsForZSet().incrementScore(key, value, delta);
    }

    /**
     * 按 score 从高到低返回指定范围内的成员，保留插入顺序
     */
    public Map<String, Double> zReverseRangeWithScores(String key, long start, long end) {
        Set<org.springframework.data.redis.core.ZSetOperations.TypedTuple<String>> typedTuples =
                stringRedisTemplate.opsForZSet().reverseRangeWithScores(key, start, end);
        Map<String, Double> result = new LinkedHashMap<>();
        if (typedTuples != null) {
            for (org.springframework.data.redis.core.ZSetOperations.TypedTuple<String> tuple : typedTuples) {
                result.put(tuple.getValue(), tuple.getScore());
            }
        }
        return result;
    }
}
