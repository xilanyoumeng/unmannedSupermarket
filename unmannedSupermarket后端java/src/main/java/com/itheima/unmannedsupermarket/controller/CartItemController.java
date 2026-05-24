package com.itheima.unmannedsupermarket.controller;

import com.itheima.unmannedsupermarket.common.Result;
import com.itheima.unmannedsupermarket.dto.CartItemAddDTO;
import com.itheima.unmannedsupermarket.dto.CartItemUpdateDTO;
import com.itheima.unmannedsupermarket.service.CartService;
import com.itheima.unmannedsupermarket.vo.CartItemVO;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/cart-item")
public class CartItemController {

    @Autowired
    private CartService cartService;

    @PostMapping("/add")
    public Result<CartItemVO> addCartItem(@Valid @RequestBody CartItemAddDTO cartItemAddDTO) {
        log.info("添加购物车明细, productId: {}, quantity: {}",
                cartItemAddDTO.getProductId(), cartItemAddDTO.getQuantity());
        CartItemVO cartItemVO = cartService.addCartItem(cartItemAddDTO);
        return Result.success(cartItemVO);
    }

    @PutMapping("/update")
    public Result<List<CartItemVO>> updateCartItems(@Valid @RequestBody CartItemUpdateDTO dto) {
        log.info("修改购物车明细, cartId: {}, items: {}", dto.getCartId(), dto.getItems());
        List<CartItemVO> voList = cartService.updateCartItems(dto);
        return Result.success(voList);
    }

    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteCartItem(@PathVariable Long id) {
        log.info("删除购物车明细, id: {}", id);
        cartService.deleteCartItem(id);
        return Result.success();
    }
}
