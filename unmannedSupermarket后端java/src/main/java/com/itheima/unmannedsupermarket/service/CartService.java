package com.itheima.unmannedsupermarket.service;

import com.itheima.unmannedsupermarket.dto.CartItemAddDTO;
import com.itheima.unmannedsupermarket.dto.CartItemUpdateDTO;
import com.itheima.unmannedsupermarket.vo.CartItemVO;
import com.itheima.unmannedsupermarket.vo.CartVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;

import java.util.List;

public interface CartService {

    PageResultVO<CartVO> getCartPage(int page, int pageSize);

    CartVO getCartDetail(Long cartId);

    CartVO updateCartName(Long cartId, String name);

    void deleteCart(Long cartId);

    CartItemVO addCartItem(CartItemAddDTO cartItemAddDTO);

    List<CartItemVO> updateCartItems(CartItemUpdateDTO dto);

    void deleteCartItem(Long itemId);
}
