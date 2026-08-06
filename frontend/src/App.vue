<template>
  <header>
    <nav>
      <div class="nav-links">
        <RouterLink to="/">Products</RouterLink>
        <RouterLink to="/cart">
          Cart
          <span v-if="cartCount > 0" class="badge">{{ cartCount }}</span>
        </RouterLink>
        <RouterLink to="/checkout">Checkout</RouterLink>
        <RouterLink to="/agent">Agent Demo</RouterLink>
      </div>
      <div class="auth-area">
        <template v-if="isLoggedIn">
          <span class="user-name">{{ current.name }}</span>
          <button class="btn-nav-ghost" @click="handleLogout">Sign out</button>
        </template>
        <template v-else>
          <button class="btn-nav-ghost" @click="openAuth('signin')">Sign in</button>
          <button class="btn-nav-solid" @click="openAuth('register')">Create account</button>
        </template>
      </div>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>

  <AuthModal
    v-if="showModal"
    :initial-mode="authMode"
    @close="showModal = false"
  />
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import AuthModal from './components/AuthModal.vue'
import { useCart } from './stores/cart.js'
import { useUser } from './stores/user.js'

const { cartCount, clearCart } = useCart()
const { current, isLoggedIn, logout } = useUser()

const showModal = ref(false)
const authMode = ref('signin')

function openAuth(mode) {
  authMode.value = mode
  showModal.value = true
}

function handleLogout() {
  logout()
  clearCart()
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, sans-serif;
  background: #f8faf5;
  color: #2d3a1e;
}

header {
  background: #3a5c2c;
  padding: 0.75rem 1.5rem;
}

nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.auth-area {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

nav a {
  color: #d4edbc;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.95rem;
  position: relative;
}

nav a:hover, nav a.router-link-active {
  color: #fff;
}

.badge {
  background: #e76b2a;
  color: #fff;
  border-radius: 9999px;
  font-size: 0.7rem;
  padding: 0.1rem 0.45rem;
  margin-left: 0.25rem;
  font-weight: 700;
}

.user-name {
  color: #d4edbc;
  font-size: 0.9rem;
  font-weight: 600;
}

.btn-nav-ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.45);
  color: #d4edbc;
  border-radius: 6px;
  padding: 0.3rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-nav-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.btn-nav-solid {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #fff;
  border-radius: 6px;
  padding: 0.3rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-nav-solid:hover {
  background: rgba(255, 255, 255, 0.25);
}

main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem;
}

h1 { font-size: 1.6rem; margin-bottom: 1rem; }
h2 { font-size: 1.2rem; margin-bottom: 0.75rem; }

button {
  cursor: pointer;
  border: none;
  border-radius: 6px;
  padding: 0.4rem 0.9rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.btn-primary {
  background: #3a5c2c;
  color: #fff;
}
.btn-primary:hover { background: #2d4820; }

.btn-secondary {
  background: #e0ead4;
  color: #3a5c2c;
}
.btn-secondary:hover { background: #ccd9b8; }

.btn-danger {
  background: #c0392b;
  color: #fff;
}

input, select {
  border: 1px solid #c5d5b0;
  border-radius: 6px;
  padding: 0.4rem 0.7rem;
  font-size: 0.9rem;
}

.error { color: #c0392b; margin: 0.5rem 0; }
.success { color: #27ae60; margin: 0.5rem 0; }
</style>
