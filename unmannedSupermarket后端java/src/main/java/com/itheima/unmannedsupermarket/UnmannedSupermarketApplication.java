package com.itheima.unmannedsupermarket;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.itheima.unmannedsupermarket.mapper")
@EnableScheduling
public class UnmannedSupermarketApplication {

    public static void main(String[] args) {
        SpringApplication.run(UnmannedSupermarketApplication.class, args);
    }

}
