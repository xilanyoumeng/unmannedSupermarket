package com.itheima.unmannedsupermarket.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itheima.unmannedsupermarket.common.RedisUtil;
import com.itheima.unmannedsupermarket.common.UserContextHolder;
import com.itheima.unmannedsupermarket.dto.CartItemAddDTO;
import com.itheima.unmannedsupermarket.dto.CartItemUpdateDTO;
import com.itheima.unmannedsupermarket.entity.Cart;
import com.itheima.unmannedsupermarket.entity.CartItem;
import com.itheima.unmannedsupermarket.entity.Product;
import com.itheima.unmannedsupermarket.mapper.CartItemMapper;
import com.itheima.unmannedsupermarket.mapper.CartMapper;
import com.itheima.unmannedsupermarket.mapper.ProductMapper;
import com.itheima.unmannedsupermarket.service.CartService;
import com.itheima.unmannedsupermarket.vo.CartItemVO;
import com.itheima.unmannedsupermarket.vo.CartVO;
import com.itheima.unmannedsupermarket.vo.PageResultVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class CartServiceImpl implements CartService {

    @Autowired
    private CartMapper cartMapper;

    @Autowired
    private CartItemMapper cartItemMapper;

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private RedisUtil redisUtil;

    @Override
    public PageResultVO<CartVO> getCartPage(int page, int pageSize) {
        Long userId = UserContextHolder.getUserId();

        // 1. 分页查购物车主表
        Page<Cart> cartPage = cartMapper.selectPage(new Page<>(page, pageSize),
                new LambdaQueryWrapper<Cart>()
                        .eq(Cart::getUserId, userId)
                        .orderByDesc(Cart::getCreateTime));

        List<Cart> carts = cartPage.getRecords();
        if (carts.isEmpty()) {
            return new PageResultVO<CartVO>()
                    .setRecords(Collections.emptyList())
                    .setTotal(0L)
                    .setPage((long) page)
                    .setPageSize((long) pageSize);
        }

        // 2. 一次查所有购物车的明细
        List<Long> cartIds = carts.stream().map(Cart::getId).collect(Collectors.toList());
        List<CartItem> allItems = cartItemMapper.selectList(
                new LambdaQueryWrapper<CartItem>().in(CartItem::getCartId, cartIds));

        // 3. 一次查所有涉及的商品
        Map<Long, Product> productMap = Collections.emptyMap();
        if (!allItems.isEmpty()) {
            List<Long> productIds = allItems.stream()
                    .map(CartItem::getProductId).distinct().collect(Collectors.toList());
            productMap = productMapper.selectBatchIds(productIds).stream()
                    .collect(Collectors.toMap(Product::getId, p -> p));
        }

        // 4. 按 cartId 分组明细
        Map<Long, List<CartItem>> itemsByCart = allItems.stream()
                .collect(Collectors.groupingBy(CartItem::getCartId));

        // 5. 组装 VO
        Map<Long, Product> finalProductMap = productMap;
        List<CartVO> voList = carts.stream()
                .map(cart -> buildCartVO(cart,
                        itemsByCart.getOrDefault(cart.getId(), Collections.emptyList()),
                        finalProductMap))
                .collect(Collectors.toList());

        return new PageResultVO<CartVO>()
                .setRecords(voList)
                .setTotal(cartPage.getTotal())
                .setPage(cartPage.getCurrent())
                .setPageSize(cartPage.getSize());
    }

    @Override
    public CartVO getCartDetail(Long cartId) {
        Cart cart = getCartWithAuth(cartId);
        return buildCartVO(cart);
    }

    @Override
    public CartVO updateCartName(Long cartId, String name) {
        Cart cart = getCartWithAuth(cartId);
        cart.setName(name);
        cartMapper.updateById(cart);
        return buildCartVO(cart);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteCart(Long cartId) {
        getCartWithAuth(cartId);
        cartItemMapper.delete(new LambdaQueryWrapper<CartItem>().eq(CartItem::getCartId, cartId));
        cartMapper.deleteById(cartId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CartItemVO addCartItem(CartItemAddDTO dto) {
        Long userId = UserContextHolder.getUserId();
        Long cartId = getOrCreateCartId(userId);

        CartItem existing = cartItemMapper.selectOne(new LambdaQueryWrapper<CartItem>()
                .eq(CartItem::getCartId, cartId)
                .eq(CartItem::getProductId, dto.getProductId()));
        if (existing != null) {
            existing.setQuantity(existing.getQuantity() + dto.getQuantity());
            cartItemMapper.updateById(existing);
            return buildCartItemVO(existing);
        }

        CartItem cartItem = new CartItem();
        cartItem.setCartId(cartId);
        cartItem.setProductId(dto.getProductId());
        cartItem.setQuantity(dto.getQuantity());
        cartItemMapper.insert(cartItem);
        return buildCartItemVO(cartItem);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<CartItemVO> updateCartItems(CartItemUpdateDTO dto) {
        // 校验购物车归属
        getCartWithAuth(dto.getCartId());

        // 先删除该购物车下所有明细
        cartItemMapper.delete(new LambdaQueryWrapper<CartItem>()
                .eq(CartItem::getCartId, dto.getCartId()));

        // 组装待插入的明细列表
        List<CartItem> newItems = new ArrayList<>();
        for (CartItemUpdateDTO.CartItemUpdateItemDTO item : dto.getItems()) {
            CartItem cartItem = new CartItem();
            cartItem.setCartId(dto.getCartId());
            cartItem.setProductId(item.getProductId());
            cartItem.setQuantity(item.getQuantity());
            newItems.add(cartItem);
        }

        if (newItems.isEmpty()) {
            return Collections.emptyList();
        }

        // 批量插入（一条 SQL）
        cartItemMapper.insertBatch(newItems);

        // 重新查询获取自增ID，再批量查商品
        List<CartItem> savedItems = cartItemMapper.selectList(
                new LambdaQueryWrapper<CartItem>().eq(CartItem::getCartId, dto.getCartId()));
        List<Long> productIds = savedItems.stream()
                .map(CartItem::getProductId).distinct().collect(Collectors.toList());
        Map<Long, Product> productMap = productMapper.selectBatchIds(productIds).stream()
                .collect(Collectors.toMap(Product::getId, p -> p));

        return savedItems.stream()
                .map(item -> buildCartItemVO(item, productMap.get(item.getProductId())))
                .collect(Collectors.toList());
    }

    @Override
    public void deleteCartItem(Long itemId) {
        CartItem cartItem = cartItemMapper.selectById(itemId);
        if (cartItem == null) {
            throw new RuntimeException("购物车明细不存在");
        }
        getCartWithAuth(cartItem.getCartId());
        cartItemMapper.deleteById(itemId);
    }

    private Long getOrCreateCartId(Long userId) {
        String canCreateKey = "cart:can_create:" + userId;
        String canCreate = redisUtil.get(canCreateKey);

        // 状态为 true：登录后第一次添加，创建新购物车，名称使用当前时间
        if ("true".equals(canCreate)) {
            Cart newCart = new Cart();
            newCart.setUserId(userId);
            String cartName = LocalDateTime.now()
                    .format(DateTimeFormatter.ofPattern("yyyy-M-d HH:mm"));
            newCart.setName(cartName);
            cartMapper.insert(newCart);

            // 第一次添加后将状态改为 false
            redisUtil.set(canCreateKey, "false");

            return newCart.getId();
        }

        // 状态为 false 或不存在：查询最新的购物车
        Cart cart = cartMapper.selectOne(new LambdaQueryWrapper<Cart>()
                .eq(Cart::getUserId, userId)
                .orderByDesc(Cart::getCreateTime)
                .last("LIMIT 1"));
        if (cart != null) {
            return cart.getId();
        }

        // 兜底：如果没有任何购物车，创建购物车，名称使用当前时间
        Cart newCart = new Cart();
        newCart.setUserId(userId);
        String cartName = LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("yyyy-M-d HH:mm"));
        newCart.setName(cartName);
        cartMapper.insert(newCart);
        return newCart.getId();
    }

    private Cart getCartWithAuth(Long cartId) {
        Long userId = UserContextHolder.getUserId();
        Cart cart = cartMapper.selectById(cartId);
        if (cart == null) {
            throw new RuntimeException("购物车不存在");
        }
        if (!cart.getUserId().equals(userId)) {
            throw new RuntimeException("无权操作该购物车");
        }
        return cart;
    }

    // ---- 单条购物车组装（详情/修改/删除场景） ----

    private CartVO buildCartVO(Cart cart) {
        List<CartItem> items = cartItemMapper.selectList(
                new LambdaQueryWrapper<CartItem>().eq(CartItem::getCartId, cart.getId()));
        if (items.isEmpty()) {
            return new CartVO()
                    .setId(cart.getId()).setUserId(cart.getUserId())
                    .setName(cart.getName()).setCreateTime(cart.getCreateTime())
                    .setItems(Collections.emptyList());
        }
        Map<Long, Product> productMap = loadProductMap(items);
        return buildCartVO(cart, items, productMap);
    }

    // ---- 批量组装（分页列表场景，避免 N+1） ----

    private CartVO buildCartVO(Cart cart, List<CartItem> items, Map<Long, Product> productMap) {
        List<CartItemVO> itemVOList = items.stream()
                .map(item -> {
                    Product product = productMap.get(item.getProductId());
                    return buildCartItemVO(item, product);
                })
                .collect(Collectors.toList());
        return new CartVO()
                .setId(cart.getId())
                .setUserId(cart.getUserId())
                .setName(cart.getName())
                .setItems(itemVOList)
                .setCreateTime(cart.getCreateTime());
    }

    private Map<Long, Product> loadProductMap(List<CartItem> items) {
        List<Long> productIds = items.stream()
                .map(CartItem::getProductId).distinct().collect(Collectors.toList());
        return productMapper.selectBatchIds(productIds).stream()
                .collect(Collectors.toMap(Product::getId, p -> p));
    }

    // ---- CartItem → CartItemVO ----

    private CartItemVO buildCartItemVO(CartItem item) {
        Product product = productMapper.selectById(item.getProductId());
        return buildCartItemVO(item, product);
    }

    private CartItemVO buildCartItemVO(CartItem item, Product product) {
        return new CartItemVO()
                .setId(item.getId())
                .setCartId(item.getCartId())
                .setProductId(item.getProductId())
                .setProductName(product != null ? product.getName() : null)
                .setProductPrice(product != null ? product.getPrice() : null)
                .setProductImage(product != null ? product.getImage() : null)
                .setQuantity(item.getQuantity())
                .setCreateTime(item.getCreateTime());
    }
}
