package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.entity.Product;
import com.itheima.unmannedsupermarket.vo.HotProductVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;

import java.util.List;

public interface ProductService {

    Product getProductById(Long id);

    Product createProduct(Product product);

    Product updateProduct(Long id, Product product);

    void deleteProduct(Long id);

    PageResultVO<Product> getProductPage(int page, int pageSize, String keyword, String category);

    PageResultVO<Product> getListedProductPage(int page, int pageSize, String keyword, String category);

    List<String> getCategories();

    void updateProductStatus(Long id, Integer status);

    List<HotProductVO> getHotProducts();
}
