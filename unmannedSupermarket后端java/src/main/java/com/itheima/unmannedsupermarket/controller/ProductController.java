package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.entity.Product;
import com.itheima.unmannedsupermarket.service.ProductService;
import com.itheima.unmannedsupermarket.vo.HotProductVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/product")
public class ProductController {

    @Autowired
    private ProductService productService;

    @GetMapping("/page")
    public Result<PageResultVO<Product>> getProductPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String category) {
        log.info("分页查询商品列表, page: {}, pageSize: {}, keyword: {}, category: {}", page, pageSize, keyword, category);
        PageResultVO<Product> pageResult = productService.getProductPage(page, pageSize, keyword, category);
        return Result.success(pageResult);
    }

    @GetMapping("/detail/{id}")
    public Result<Product> getProductDetail(@PathVariable Long id) {
        log.info("查询商品详情, id: {}", id);
        Product product = productService.getProductById(id);
        return Result.success(product);
    }

    @PostMapping("/add")
    public Result<Product> createProduct(@RequestBody Product product) {
        log.info("新增商品, name: {}", product.getName());
        Product created = productService.createProduct(product);
        return Result.success(created);
    }

    @PutMapping("/update/{id}")
    public Result<Product> updateProduct(@PathVariable Long id, @RequestBody Product product) {
        log.info("修改商品, id: {}", id);
        Product updated = productService.updateProduct(id, product);
        return Result.success(updated);
    }

    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteProduct(@PathVariable Long id) {
        log.info("删除商品, id: {}", id);
        productService.deleteProduct(id);
        return Result.success();
    }

    @GetMapping("/listed")
    public Result<PageResultVO<Product>> getListedProductPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String category) {
        log.info("查询上架商品列表, page: {}, pageSize: {}, keyword: {}, category: {}", page, pageSize, keyword, category);
        PageResultVO<Product> pageResult = productService.getListedProductPage(page, pageSize, keyword, category);
        return Result.success(pageResult);
    }

    @GetMapping("/categories")
    public Result<List<String>> getCategories() {
        log.info("查询商品分类列表");
        List<String> categories = productService.getCategories();
        return Result.success(categories);
    }

    @GetMapping("/hot")
    public Result<List<HotProductVO>> getHotProducts() {
        log.info("查询热销商品");
        List<HotProductVO> hotProducts = productService.getHotProducts();
        return Result.success(hotProducts);
    }

    @PutMapping("/status/{id}")
    public Result<Void> updateProductStatus(@PathVariable Long id, @RequestParam Integer status) {
        log.info("修改商品状态, id: {}, status: {}", id, status);
        productService.updateProductStatus(id, status);
        return Result.success();
    }
}
