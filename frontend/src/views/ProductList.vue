<template>
  <div>
    <h1>Garden Products</h1>

    <div class="filters">
      <select v-model="selectedCategory" @change="loadProducts">
        <option value="">All categories</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
      <input
        v-model.number="maxPrice"
        type="number"
        min="0"
        step="0.01"
        placeholder="Max price"
        @change="loadProducts"
      />
      <button class="btn-secondary" @click="clearFilters">Clear</button>
    </div>

    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else class="grid">
      <div v-for="product in products" :key="product.id" class="card">
        <div class="card-category">{{ product.category }}</div>
        <h2>{{ product.name }}</h2>
        <p class="description">{{ product.description }}</p>
        <div class="card-footer">
          <span class="price">£{{ product.price.toFixed(2) }}</span>
          <span class="stock" :class="{ 'low-stock': product.stock_qty < 10 }">
            {{ product.stock_qty }} in stock
          </span>
          <button
            class="btn-primary"
            :disabled="product.stock_qty === 0"
            @click="addToCart(product)"
          >
            {{ product.stock_qty === 0 ? 'Out of stock' : 'Add to cart' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchProducts } from '../api/client.js'
import { useCart } from '../stores/cart.js'

const products = ref([])
const loading = ref(false)
const error = ref(null)
const selectedCategory = ref('')
const maxPrice = ref(null)

const { addToCart } = useCart()

const categories = computed(() => {
  const seen = new Set()
  for (const p of products.value) if (p.category) seen.add(p.category)
  return [...seen].sort()
})

async function loadProducts() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (selectedCategory.value) params.category = selectedCategory.value
    if (maxPrice.value != null && maxPrice.value > 0) params.max_price = maxPrice.value
    products.value = await fetchProducts(params)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  selectedCategory.value = ''
  maxPrice.value = null
  loadProducts()
}

onMounted(loadProducts)
</script>

<style scoped>
.filters {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  align-items: center;
  flex-wrap: wrap;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.card {
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.card-category {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #7a9b5a;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.description {
  font-size: 0.85rem;
  color: #556b3a;
  flex: 1;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.price {
  font-weight: 700;
  font-size: 1rem;
  color: #2d3a1e;
  flex: 1;
}

.stock {
  font-size: 0.75rem;
  color: #7a9b5a;
}

.low-stock {
  color: #e76b2a;
}
</style>
