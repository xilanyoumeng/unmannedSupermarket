import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Cart, CartItem } from '../types'
import {
  getCartPageApi,
  getCartDetailApi,
  addCartItemApi,
  updateCartItemApi,
  deleteCartApi
} from '../api/cart'

export const useCartStore = defineStore('cart', () => {
  const carts = ref<Cart[]>([])
  const activeCartId = ref<number | null>(null)
  const items = ref<CartItem[]>([])

  const totalCount = computed(() => items.value.reduce((sum, i) => sum + i.quantity, 0))
  const totalPrice = computed(() => items.value.reduce((sum, i) => sum + i.productPrice * i.quantity, 0))

  async function fetchCart() {
    try {
      const pageRes = await getCartPageApi({ page: 1, pageSize: 50 })
      carts.value = pageRes.data.data?.records ?? []
if (carts.value.length > 0) {
        if (!activeCartId.value || !carts.value.find(c => c.id === activeCartId.value)) {
          activeCartId.value = carts.value[0].id
        }
        const cart = carts.value.find(c => c.id === activeCartId.value)
        items.value = cart?.items?.length ? [...cart.items] : items.value
      } else {
        activeCartId.value = null
        items.value = []
      }
    } catch {
      carts.value = []
    }
  }

  async function selectCart(id: number) {
    activeCartId.value = id
    try {
      const res = await getCartDetailApi(id)
      const cart = res.data.data
      items.value = cart?.items ? [...cart.items] : []
      const idx = carts.value.findIndex(c => c.id === id)
      if (idx >= 0 && cart) {
        carts.value[idx] = { ...carts.value[idx], name: cart.name, items: cart.items ?? [] }
      }
    } catch {
      const cart = carts.value.find(c => c.id === id)
      items.value = cart?.items ? [...cart.items] : []
    }
  }

  async function addToCart(productId: number, quantity = 1) {
    await addCartItemApi({ productId, quantity })
    await fetchCart()
  }

  function updateQuantity(cartItemId: number, quantity: number) {
    const item = items.value.find(i => i.id === cartItemId)
    if (item) item.quantity = quantity
  }

  function removeItem(cartItemId: number) {
    items.value = items.value.filter(i => i.id !== cartItemId)
  }

  async function saveCart() {
    if (!activeCartId.value) return
    await updateCartItemApi({
      cartId: activeCartId.value,
      items: items.value.map(item => ({
        productId: item.productId,
        quantity: item.quantity
      }))
    })
    await fetchCart()
  }

  async function clearCart() {
    if (activeCartId.value) {
      try {
        await deleteCartApi(activeCartId.value)
      } catch { /* 即使删除失败也重置本地状态 */ }
    }
    carts.value = carts.value.filter(c => c.id !== activeCartId.value)
    activeCartId.value = carts.value.length > 0 ? carts.value[0].id : null
    if (activeCartId.value) {
      const cart = carts.value.find(c => c.id === activeCartId.value)
      items.value = cart?.items ? [...cart.items] : []
    } else {
      items.value = []
    }
  }

  function resetCart() {
    carts.value = []
    activeCartId.value = null
    items.value = []
  }

  return {
    carts,
    activeCartId,
    items,
    totalCount,
    totalPrice,
    fetchCart,
    selectCart,
    addToCart,
    saveCart,
    updateQuantity,
    removeItem,
    clearCart,
    resetCart
  }
})
