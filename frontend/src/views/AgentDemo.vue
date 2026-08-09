<template>
  <div>
    <h1>Agent Demo</h1>
    <p style="color:#556b3a;margin-bottom:1rem;">
      Send raw JSON intents directly to the Garden Store Agent via the A2A JSON-RPC endpoint
      (<code>/rpc</code>).
    </p>

    <div class="examples">
      <h2>Example intents</h2>
      <div class="example-btns">
        <button
          v-for="ex in examples"
          :key="ex.label"
          class="btn-secondary"
          @click="input = ex.json"
        >
          {{ ex.label }}
        </button>
      </div>
    </div>

    <div class="panel">
      <div class="pane">
        <h2>Request</h2>
        <textarea v-model="input" rows="8" spellcheck="false" placeholder='{"action":"browse_products"}'></textarea>
        <button class="btn-primary" :disabled="sending" @click="send">
          {{ sending ? 'Sending…' : 'Send to agent' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </div>

      <div class="pane">
        <h2>Response</h2>
        <pre v-if="response">{{ JSON.stringify(response, null, 2) }}</pre>
        <p v-else style="color:#aaa;font-style:italic">Response will appear here.</p>
      </div>
    </div>

    <div class="card-section">
      <h2>Agent card</h2>
      <button class="btn-secondary" @click="fetchCard">Fetch /.well-known/agent-card.json</button>
      <pre v-if="agentCard">{{ JSON.stringify(agentCard, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { a2aRpc } from '../api/client.js'

const input = ref('')
const response = ref(null)
const error = ref(null)
const sending = ref(false)
const agentCard = ref(null)

const examples = [
  { label: 'List categories', json: JSON.stringify({ action: 'list_categories' }) },
  { label: 'Browse all', json: JSON.stringify({ action: 'browse_products' }) },
  { label: 'Browse seeds', json: JSON.stringify({ action: 'browse_products', category: 'seeds' }) },
  { label: 'Get product #1', json: JSON.stringify({ action: 'get_product', product_id: 1 }) },
  {
    label: 'Create customer',
    json: JSON.stringify({ action: 'create_customer', name: 'Alice Green', email: 'alice@example.com' }),
  },
  {
    label: 'Checkout',
    json: JSON.stringify({
      action: 'checkout',
      customer_email: 'alice@example.com',
      items: [{ product_id: 1, quantity: 1 }],
    }),
  },
  {
    label: 'List purchases',
    json: JSON.stringify({ action: 'list_purchases', customer_email: 'alice@example.com' }),
  },
]

async function send() {
  sending.value = true
  error.value = null
  response.value = null
  try {
    response.value = await a2aRpc(input.value)
  } catch (e) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}

async function fetchCard() {
  const res = await fetch('/.well-known/agent-card.json')
  agentCard.value = await res.json()
}
</script>

<style scoped>
.examples {
  margin-bottom: 1rem;
}

.example-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

@media (max-width: 700px) {
  .panel { grid-template-columns: 1fr; }
}

.pane {
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

textarea {
  width: 100%;
  font-family: monospace;
  font-size: 0.85rem;
  border: 1px solid #c5d5b0;
  border-radius: 6px;
  padding: 0.5rem;
  resize: vertical;
  background: #f8faf5;
}

pre {
  background: #f0f5e8;
  border: 1px solid #c5d5b0;
  border-radius: 8px;
  padding: 0.75rem;
  font-size: 0.8rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
}

.card-section {
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
</style>
