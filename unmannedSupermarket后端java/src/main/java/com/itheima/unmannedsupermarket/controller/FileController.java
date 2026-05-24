package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.service.OssService;
import com.itheima.unmannedsupermarket.vo.ImageUploadVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Slf4j
@RestController
@RequestMapping("/api/file")
public class FileController {

    @Autowired
    private OssService ossService;

    @PostMapping("/upload")
    public Result<ImageUploadVO> uploadImage(@RequestParam("file") MultipartFile file) {
        log.info("上传图片, filename: {}, size: {}", file.getOriginalFilename(), file.getSize());
        ImageUploadVO result = ossService.upload(file, "announcement");
        return Result.success(result);
    }
}
