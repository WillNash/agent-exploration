<template>
  <div>
    <h1>Checkout</h1>

    <div v-if="confirmed" class="confirmation">
      <h2>Order confirmed!</h2>
      <p>Thank you, {{ confirmedName }}. Your order total was <strong>£{{ orderTotal }}</strong>.</p>
      <table>
        <thead>
          <tr><th>Product</th><th>Qty</th><th>Line total</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in confirmedItems" :key="item.purchase_id">
            <td>{{ item.product_name }}</td>
            <td>{{ item.quantity }}</td>
            <td>£{{ item.line_total.toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <RouterLink to="/" class="btn-primary" style="display:inline-block;margin-top:1rem;padding:0.4rem 0.9rem;border-radius:6px;text-decoration:none;color:#fff;">
        Continue shopping
      </RouterLink>
    </div>

    <template v-else>
      <p v-if="items.length === 0">
        Your cart is empty.
        <RouterLink to="/">Browse products</RouterLink>
      </p>

      <template v-else>
        <div class="summary">
          <h2>Order summary</h2>
          <ul>
            <li v-for="item in items" :key="item.product.id">
              {{ item.product.name }} × {{ item.quantity }} —
              £{{ (item.product.price * item.quantity).toFixed(2) }}
            </li>
          </ul>
          <p><strong>Total: £{{ cartTotal.toFixed(2) }}</strong></p>
        </div>

        <form @submit.prevent="submit">
          <div v-if="isLoggedIn" class="logged-in-as">
            <span>Checking out as <strong>{{ current.name }}</strong> ({{ current.email }})</span>
            <span class="not-you">Not you? Sign out from the menu above.</span>
          </div>
          <template v-else>
            <div class="field">
              <label for="name">Full name</label>
              <input id="name" v-model="name" type="text" required placeholder="Alice Green" />
            </div>
            <div class="field">
              <label for="email">Email</label>
              <input id="email" v-model="email" type="email" required placeholder="alice@example.com" />
            </div>
          </template>
          <p v-if="error" class="error">{{ error }}</p>
          <button class="btn-primary" type="submit" :disabled="submitting">
            {{ submitting ? 'Placing order…' : 'Place order' }}
          </button>
        </form>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createCustomer, a2aRpc } from '../api/client.js'
import { useCart } from '../stores/cart.js'
import { useUser } from '../stores/user.js'

const { items, cartTotal, clearCart } = useCart()
const { current, isLoggedIn, login } = useUser()

const name = ref('')
const email = ref('')
const submitting = ref(false)
const error = ref(null)
const confirmed = ref(false)
const confirmedName = ref('')
const confirmedItems = ref([])
const orderTotal = ref('0.00')

async function submit() {
  submitting.value = true
  error.value = null
  try {
    const customerEmail = isLoggedIn.value ? current.value.email : email.value
    const customerName = isLoggedIn.value ? current.value.name : name.value

    if (!isLoggedIn.value) {
      const customer = await createCustomer({ name: customerName, email: customerEmail })
      login(customer)
    }

    const intent = {
      action: 'checkout',
      customer_email: customerEmail,
      items: items.value.map((i) => ({
        product_id: i.product.id,
        quantity: i.quantity,
      })),
    }

    const task = await a2aRpc(JSON.stringify(intent))

    const artifactText = task?.message?.parts?.[0]?.text
    if (!artifactText) throw new Error('No response from agent')

    const result = JSON.parse(artifactText)
    if (result.error) throw new Error(result.error)

    confirmedName.value = customerName
    confirmedItems.value = result.items ?? []
    orderTotal.value = (result.order_total ?? 0).toFixed(2)
    confirmed.value = true
    clearCart()
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.confirmation {
  background: #eef9e8;
  border: 1px solid #a8d38a;
  border-radius: 10px;
  padding: 1.25rem;
}

.confirmation table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.75rem;
}

.confirmation th, .confirmation td {
  padding: 0.5rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid #c5e8a8;
}

.summary {
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
}

.summary ul {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}

.summary li {
  padding: 0.2rem 0;
  font-size: 0.9rem;
  color: #4a6030;
}

form {
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 10px;
  padding: 1.25rem;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.logged-in-as {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.6rem 0.75rem;
  background: #f0f7ea;
  border: 1px solid #c5dfa8;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #3a5c2c;
}

.not-you {
  font-size: 0.78rem;
  color: #7a9a6a;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #3a5c2c;
}

input {
  width: 100%;
}
</style>
