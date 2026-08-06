import { computed, ref } from 'vue'

const _KEY = 'garden_user'

function _load() {
  try {
    const raw = localStorage.getItem(_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const _current = ref(_load())

export function useUser() {
  const isLoggedIn = computed(() => _current.value !== null)

  function login(customer) {
    _current.value = customer
    localStorage.setItem(_KEY, JSON.stringify(customer))
  }

  function logout() {
    _current.value = null
    localStorage.removeItem(_KEY)
  }

  return { current: _current, isLoggedIn, login, logout }
}
