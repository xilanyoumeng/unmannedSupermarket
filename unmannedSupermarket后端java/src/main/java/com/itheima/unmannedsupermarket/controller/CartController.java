package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import com.itheima.unmannedsupermarket.service.CartService;
import com.itheima.unmannedsupermarket.vo.CartVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/cart")
public class CartController {

    @Autowired
    private CartService cartService;

    @GetMapping("/page")
    public Result<PageResultVO<CartVO>> getCartPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        Long userId = UserContextHolder.getUserId();
        log.info("分页查询购物车列表, userId: {}, page: {}, pageSize: {}", userId, page, pageSize);
        PageResultVO<CartVO> pageResult = cartService.getCartPage(page, pageSize);
        return Result.success(pageResult);
    }

    @GetMapping("/detail/{id}")
    public Result<CartVO> getCartDetail(@PathVariable Long id) {
        log.info("查询购物车详情, id: {}", id);
        CartVO cartVO = cartService.getCartDetail(id);
        return Result.success(cartVO);
    }

    @PutMapping("/update/{id}")
    public Result<CartVO> updateCartName(@PathVariable Long id, @RequestParam String name) {
        log.info("修改购物车名称, id: {}, name: {}", id, name);
        CartVO cartVO = cartService.updateCartName(id, name);
        return Result.success(cartVO);
    }

    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteCart(@PathVariable Long id) {
        log.info("删除购物车, id: {}", id);
        cartService.deleteCart(id);
        return Result.success();
    }
}
