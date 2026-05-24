package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.vo.ImageUploadVO;
import org.springframework.web.multipart.MultipartFile;

public interface OssService {

    /**
     * Upload a file to Alibaba Cloud OSS
     * @param file the file to upload
     * @param directory the directory prefix (e.g., "announcement")
     * @return the uploaded file info
     */
    ImageUploadVO upload(MultipartFile file, String directory);
}
