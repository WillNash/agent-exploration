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
  const token = computed(() => _current.value?.token ?? null)

  function login(customer, accessToken) {
    const stored = { ...customer, token: accessToken }
    _current.value = stored
    localStorage.setItem(_KEY, JSON.stringify(stored))
  }

  function logout() {
    _current.value = null
    localStorage.removeItem(_KEY)
  }

  return { current: _current, token, isLoggedIn, login, logout }
}
