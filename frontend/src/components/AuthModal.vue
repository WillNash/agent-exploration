<template>
  <Teleport to="body">
    <div class="backdrop" @click.self="$emit('close')">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Account">
        <button class="close-btn" @click="$emit('close')" aria-label="Close">×</button>

        <div class="tabs">
          <button
            :class="['tab', { active: mode === 'signin' }]"
            type="button"
            @click="switchMode('signin')"
          >Sign in</button>
          <button
            :class="['tab', { active: mode === 'register' }]"
            type="button"
            @click="switchMode('register')"
          >Create account</button>
        </div>

        <form v-if="mode === 'signin'" @submit.prevent="doSignIn">
          <p class="hint">No password needed — just your email.</p>
          <div class="field">
            <label for="auth-email">Email</label>
            <input
              id="auth-email"
              v-model="email"
              type="email"
              required
              autofocus
              placeholder="alice@example.com"
            />
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button class="btn-primary submit-btn" type="submit" :disabled="loading">
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
          <p class="switch-hint">
            No account?
            <button type="button" class="link-btn" @click="switchMode('register')">Create one</button>
          </p>
        </form>

        <form v-else @submit.prevent="doCreate">
          <div class="field">
            <label for="auth-name">Full name</label>
            <input
              id="auth-name"
              v-model="name"
              type="text"
              required
              autofocus
              placeholder="Alice Green"
            />
          </div>
          <div class="field">
            <label for="auth-email2">Email</label>
            <input
              id="auth-email2"
              v-model="email"
              type="email"
              required
              placeholder="alice@example.com"
            />
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button class="btn-primary submit-btn" type="submit" :disabled="loading">
            {{ loading ? 'Creating…' : 'Create account' }}
          </button>
          <p class="switch-hint">
            Already have one?
            <button type="button" class="link-btn" @click="switchMode('signin')">Sign in</button>
          </p>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { createCustomer, lookupCustomer } from '../api/client.js'
import { useUser } from '../stores/user.js'

const props = defineProps({
  initialMode: { type: String, default: 'signin' },
})
const emit = defineEmits(['close'])

const { login } = useUser()

const mode = ref(props.initialMode)
const name = ref('')
const email = ref('')
const error = ref(null)
const loading = ref(false)

function switchMode(m) {
  mode.value = m
  error.value = null
}

async function doSignIn() {
  loading.value = true
  error.value = null
  try {
    const customer = await lookupCustomer(email.value)
    login(customer)
    emit('close')
  } catch (e) {
    error.value = e.message.startsWith('404')
      ? 'No account found with that email.'
      : e.message
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  loading.value = true
  error.value = null
  try {
    const customer = await createCustomer({ name: name.value, email: email.value })
    login(customer)
    emit('close')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: #fff;
  border-radius: 12px;
  padding: 1.75rem 2rem;
  width: 100%;
  max-width: 380px;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}

.close-btn {
  position: absolute;
  top: 0.75rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.4rem;
  color: #888;
  cursor: pointer;
  line-height: 1;
  padding: 0.25rem;
}
.close-btn:hover { color: #333; }

.tabs {
  display: flex;
  gap: 0;
  margin-bottom: 1.25rem;
  border-bottom: 2px solid #e0ead4;
}

.tab {
  background: none;
  border: none;
  padding: 0.5rem 1rem 0.6rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #7a9a6a;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab.active {
  color: #3a5c2c;
  border-bottom-color: #3a5c2c;
}
.tab:hover:not(.active) { color: #3a5c2c; }

form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.hint {
  font-size: 0.82rem;
  color: #6a8a5a;
  margin: 0;
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

.submit-btn {
  width: 100%;
  padding: 0.55rem;
  font-size: 0.95rem;
}

.switch-hint {
  font-size: 0.82rem;
  color: #6a8a5a;
  text-align: center;
  margin: 0;
}

.link-btn {
  background: none;
  border: none;
  color: #3a5c2c;
  font-weight: 600;
  font-size: inherit;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}
.link-btn:hover { color: #2d4820; }
</style>
