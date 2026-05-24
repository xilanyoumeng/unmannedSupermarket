package com.itheima.unmannedsupermarket.service.impl;

import com.aliyun.oss.OSS;
import com.aliyun.oss.OSSClientBuilder;
import com.itheima.unmannedsupermarket.config.OssProperties;
import com.itheima.unmannedsupermarket.service.OssService;
import com.itheima.unmannedsupermarket.vo.ImageUploadVO;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

@Slf4j
@Service
public class OssServiceImpl implements OssService {

    @Autowired
    private OssProperties ossProperties;

    private OSS ossClient;

    @PostConstruct
    public void init() {
        ossClient = new OSSClientBuilder().build(
                ossProperties.getEndpoint(),
                ossProperties.getAccessKeyId(),
                ossProperties.getAccessKeySecret());
        log.info("OSS client initialized, endpoint: {}, bucket: {}",
                ossProperties.getEndpoint(), ossProperties.getBucketName());
    }

    @PreDestroy
    public void destroy() {
        if (ossClient != null) {
            ossClient.shutdown();
        }
    }

    @Override
    public ImageUploadVO upload(MultipartFile file, String directory) {
        validateImage(file);

        String originalFilename = file.getOriginalFilename();
        String extension = getExtension(originalFilename);
        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        String objectKey = String.format("%s/%s/%s%s",
                directory, datePath, UUID.randomUUID(), extension);

        try {
            ossClient.putObject(
                    ossProperties.getBucketName(),
                    objectKey,
                    file.getInputStream());
            log.info("File uploaded to OSS: {}", objectKey);
        } catch (IOException e) {
            log.error("Failed to upload file to OSS", e);
            throw new RuntimeException("文件上传失败", e);
        }

        String baseUrl = String.format("https://%s.%s/",
                ossProperties.getBucketName(), ossProperties.getEndpoint());
        return new ImageUploadVO().setUrl(baseUrl + objectKey);
    }

    private void validateImage(MultipartFile file) {
        if (file.isEmpty()) {
            throw new IllegalArgumentException("文件不能为空");
        }
        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            throw new IllegalArgumentException("只允许上传图片文件");
        }
    }

    private String getExtension(String filename) {
        if (filename == null || !filename.contains(".")) {
            return ".png";
        }
        return filename.substring(filename.lastIndexOf("."));
    }
}
