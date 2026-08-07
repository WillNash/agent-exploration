<template>
  <div>
    <h1>Account</h1>

    <div class="profile-card">
      <p><strong>{{ current.name }}</strong></p>
      <p class="email">{{ current.email }}</p>
    </div>

    <section class="token-section">
      <h2>Developer tokens</h2>
      <p class="hint">
        Use a token to authenticate the agent CLI without typing your password.
        Tokens are long-lived and revocable — treat them like passwords.
      </p>

      <form class="create-form" @submit.prevent="createToken">
        <input
          v-model="newTokenName"
          placeholder="Token label, e.g. my laptop"
          required
          :disabled="creating"
        />
        <button class="btn-primary" type="submit" :disabled="creating || !newTokenName.trim()">
          {{ creating ? 'Creating…' : 'Create token' }}
        </button>
      </form>
      <p v-if="createError" class="error">{{ createError }}</p>

      <div v-if="newToken" class="new-token-box">
        <p class="new-token-label">
          Copy this token now — it won't be shown again.
        </p>
        <div class="token-row">
          <code class="token-value">{{ newToken }}</code>
          <button class="btn-secondary copy-btn" @click="copyToken">
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
        <p class="agent-hint">
          Pass it to the agent: <code>python agent_client/agent.py --token &lt;paste&gt;</code>
        </p>
      </div>

      <div v-if="tokens.length > 0" class="token-list">
        <div
          v-for="t in tokens"
          :key="t.id"
          :class="['token-item', { revoked: t.revoked_at }]"
        >
          <div class="token-meta">
            <span class="token-name">{{ t.name }}</span>
            <span class="token-date">Created {{ formatDate(t.created_at) }}</span>
            <span v-if="t.revoked_at" class="revoked-badge">Revoked</span>
          </div>
          <button
            v-if="!t.revoked_at"
            class="btn-danger revoke-btn"
            @click="revokeToken(t.id)"
          >
            Revoke
          </button>
        </div>
      </div>
      <p v-else-if="loaded" class="no-tokens">No tokens yet.</p>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { createDeveloperToken, listDeveloperTokens, revokeDeveloperToken } from '../api/client.js'

const tokens = ref([])
const loaded = ref(false)
const newTokenName = ref('')
const newToken = ref(null)
const creating = ref(false)
const createError = ref(null)
const copied = ref(false)

import { useUser } from '../stores/user.js'
const { current } = useUser()

onMounted(async () => {
  tokens.value = await listDeveloperTokens()
  loaded.value = true
})

async function createToken() {
  creating.value = true
  createError.value = null
  newToken.value = null
  try {
    const result = await createDeveloperToken(newTokenName.value.trim())
    newToken.value = result.token
    newTokenName.value = ''
    tokens.value = await listDeveloperTokens()
  } catch (e) {
    createError.value = e.message
  } finally {
    creating.value = false
  }
}

async function revokeToken(id) {
  await revokeDeveloperToken(id)
  tokens.value = await listDeveloperTokens()
}

function copyToken() {
  navigator.clipboard.writeText(newToken.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}
</script>

<style scoped>
.profile-card {
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  max-width: 480px;
}

.email { color: #6a8a5a; font-size: 0.9rem; margin-top: 0.2rem; }

.token-section { max-width: 640px; }

.hint {
  color: #6a8a5a;
  font-size: 0.88rem;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.create-form {
  display: flex;
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}

.create-form input {
  flex: 1;
  padding: 0.4rem 0.7rem;
}

.new-token-box {
  background: #fffbe6;
  border: 1px solid #f0d060;
  border-radius: 8px;
  padding: 0.9rem 1rem;
  margin-bottom: 1rem;
}

.new-token-label {
  font-weight: 600;
  font-size: 0.88rem;
  color: #7a5c00;
  margin-bottom: 0.5rem;
}

.token-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
}

.token-value {
  flex: 1;
  font-size: 0.75rem;
  word-break: break-all;
  background: #fff8d0;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #e8d080;
}

.copy-btn { flex-shrink: 0; }

.agent-hint {
  font-size: 0.82rem;
  color: #7a5c00;
}

.agent-hint code {
  background: #fff8d0;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

.token-list { display: flex; flex-direction: column; gap: 0.5rem; }

.token-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #dce8cc;
  border-radius: 8px;
  padding: 0.65rem 1rem;
}

.token-item.revoked {
  background: #fafafa;
  opacity: 0.65;
}

.token-meta {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.token-name { font-weight: 600; font-size: 0.9rem; }

.token-date { font-size: 0.8rem; color: #6a8a5a; }

.revoked-badge {
  font-size: 0.75rem;
  color: #c0392b;
  font-weight: 600;
}

.revoke-btn { font-size: 0.8rem; padding: 0.25rem 0.6rem; }

.no-tokens { color: #6a8a5a; font-size: 0.9rem; margin-top: 0.5rem; }
</style>
