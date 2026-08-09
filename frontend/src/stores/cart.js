import { computed, ref } from 'vue'

const items = ref([])

export function useCart() {
  function addToCart(product) {
    const existing = items.value.find((i) => i.product.id === product.id)
    if (existing) {
      existing.quantity += 1
    } else {
      items.value.push({ product, quantity: 1 })
    }
  }

  function removeFromCart(productId) {
    items.value = items.value.filter((i) => i.product.id !== productId)
  }

  function updateQuantity(productId, qty) {
    const item = items.value.find((i) => i.product.id === productId)
    if (!item) return
    if (qty <= 0) {
      removeFromCart(productId)
    } else {
      item.quantity = qty
    }
  }

  function clearCart() {
    items.value = []
  }

  const cartTotal = computed(() =>
    items.value.reduce((sum, i) => sum + i.product.price * i.quantity, 0)
  )

  const cartCount = computed(() =>
    items.value.reduce((sum, i) => sum + i.quantity, 0)
  )

  return { items, addToCart, removeFromCart, updateQuantity, clearCart, cartTotal, cartCount }
}
