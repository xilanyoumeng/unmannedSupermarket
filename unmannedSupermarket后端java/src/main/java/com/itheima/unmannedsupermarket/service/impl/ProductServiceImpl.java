package com.itheima.unmannedsupermarket.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itheima.unmannedsupermarket.common.RedisUtil;
import com.itheima.unmannedsupermarket.entity.Product;
import com.itheima.unmannedsupermarket.mapper.ProductMapper;
import com.itheima.unmannedsupermarket.service.ProductService;
import com.itheima.unmannedsupermarket.vo.HotProductVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class ProductServiceImpl implements ProductService {

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private RedisUtil redisUtil;

    @Override
    public Product getProductById(Long id) {
        Product product = productMapper.selectById(id);
        if (product == null) {
            throw new RuntimeException("商品不存在");
        }
        return product;
    }

    @Override
    public Product createProduct(Product product) {
        product.setStatus(product.getStatus() != null ? product.getStatus() : 1);
        productMapper.insert(product);
        return product;
    }

    @Override
    public Product updateProduct(Long id, Product product) {
        Product existing = getProductById(id);
        if (product.getName() != null) {
            existing.setName(product.getName());
        }
        if (product.getPrice() != null) {
            existing.setPrice(product.getPrice());
        }
        if (product.getStock() != null) {
            existing.setStock(product.getStock());
        }
        if (product.getCategory() != null) {
            existing.setCategory(product.getCategory());
        }
        if (product.getDescription() != null) {
            existing.setDescription(product.getDescription());
        }
        if (product.getImage() != null) {
            existing.setImage(product.getImage());
        }
        if (product.getBarcode() != null) {
            existing.setBarcode(product.getBarcode());
        }
        if (product.getStatus() != null) {
            existing.setStatus(product.getStatus());
        }
        productMapper.updateById(existing);
        return existing;
    }

    @Override
    public void deleteProduct(Long id) {
        getProductById(id);
        productMapper.deleteById(id);
    }

    @Override
    public PageResultVO<Product> getProductPage(int page, int pageSize, String keyword, String category) {
        LambdaQueryWrapper<Product> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(keyword)) {
            wrapper.and(w -> w.like(Product::getName, keyword)
                    .or().like(Product::getDescription, keyword));
        }
        if (StringUtils.hasText(category)) {
            wrapper.eq(Product::getCategory, category);
        }
        wrapper.orderByDesc(Product::getCreateTime);
        Page<Product> productPage = productMapper.selectPage(new Page<>(page, pageSize), wrapper);
        return new PageResultVO<Product>()
                .setRecords(productPage.getRecords())
                .setTotal(productPage.getTotal())
                .setPage(productPage.getCurrent())
                .setPageSize(productPage.getSize());
    }

    @Override
    public PageResultVO<Product> getListedProductPage(int page, int pageSize, String keyword, String category) {
        LambdaQueryWrapper<Product> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Product::getStatus, 1);
        if (StringUtils.hasText(keyword)) {
            wrapper.and(w -> w.like(Product::getName, keyword)
                    .or().like(Product::getDescription, keyword));
        }
        if (StringUtils.hasText(category)) {
            wrapper.eq(Product::getCategory, category);
        }
        wrapper.orderByDesc(Product::getCreateTime);
        Page<Product> productPage = productMapper.selectPage(new Page<>(page, pageSize), wrapper);
        return new PageResultVO<Product>()
                .setRecords(productPage.getRecords())
                .setTotal(productPage.getTotal())
                .setPage(productPage.getCurrent())
                .setPageSize(productPage.getSize());
    }

    @Override
    public List<String> getCategories() {
        return productMapper.selectDistinctCategories();
    }

    @Override
    public void updateProductStatus(Long id, Integer status) {
        Product product = getProductById(id);
        product.setStatus(status);
        productMapper.updateById(product);
    }

    @Override
    public List<HotProductVO> getHotProducts() {
        Map<String, Double> hotMap = redisUtil.zReverseRangeWithScores("hot:products", 0, 2);
        if (hotMap == null || hotMap.isEmpty()) {
            return List.of();
        }
        List<Long> productIds = new ArrayList<>();
        for (String idStr : hotMap.keySet()) {
            productIds.add(Long.valueOf(idStr));
        }
        List<Product> products = productMapper.selectBatchIds(productIds);
        List<HotProductVO> result = new ArrayList<>();
        for (Long productId : productIds) {
            Product product = products.stream()
                    .filter(p -> p.getId().equals(productId))
                    .findFirst()
                    .orElse(null);
            if (product != null && product.getStatus() != null && product.getStatus() == 1) {
                int hotCount = hotMap.get(productId.toString()).intValue();
                result.add(HotProductVO.fromProduct(product, hotCount));
            }
        }
        return result;
    }
}
