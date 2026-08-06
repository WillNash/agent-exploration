<template>
  <div>
    <h1>Your Cart</h1>

    <p v-if="items.length === 0">
      Your cart is empty.
      <RouterLink to="/">Browse products</RouterLink>
    </p>

    <template v-else>
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Qty</th>
            <th>Line total</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.product.id">
            <td>{{ item.product.name }}</td>
            <td>£{{ item.product.price.toFixed(2) }}</td>
            <td>
              <div class="qty-controls">
                <button @click="updateQuantity(item.product.id, item.quantity - 1)">−</button>
                <span>{{ item.quantity }}</span>
                <button @click="updateQuantity(item.product.id, item.quantity + 1)">+</button>
              </div>
            </td>
            <td>£{{ (item.product.price * item.quantity).toFixed(2) }}</td>
            <td>
              <button class="btn-danger" @click="removeFromCart(item.product.id)">Remove</button>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="3"><strong>Total</strong></td>
            <td colspan="2"><strong>£{{ cartTotal.toFixed(2) }}</strong></td>
          </tr>
        </tfoot>
      </table>

      <div class="actions">
        <RouterLink to="/" class="btn-secondary" style="padding:0.4rem 0.9rem;border-radius:6px;text-decoration:none;font-weight:600;">
          Continue shopping
        </RouterLink>
        <RouterLink to="/checkout" class="btn-primary" style="padding:0.4rem 0.9rem;border-radius:6px;text-decoration:none;font-weight:600;color:#fff;">
          Proceed to checkout
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { useCart } from '../stores/cart.js'

const { items, removeFromCart, updateQuantity, cartTotal } = useCart()
</script>

<style scoped>
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 1.25rem;
}

th, td {
  padding: 0.65rem 1rem;
  text-align: left;
  border-bottom: 1px solid #dce8cc;
}

th {
  background: #eef5e6;
  font-size: 0.82rem;
  text-transform: uppercase;
  color: #7a9b5a;
  letter-spacing: 0.04em;
}

tfoot td {
  border-bottom: none;
  background: #f4f9ec;
}

.qty-controls {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.qty-controls button {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid #c5d5b0;
  background: #eef5e6;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}
</style>
