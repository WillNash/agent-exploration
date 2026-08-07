const BASE = ''

function getToken() {
  try {
    const raw = localStorage.getItem('garden_user')
    return raw ? JSON.parse(raw).token : null
  } catch {
    return null
  }
}

async function request(method, path, body, { auth = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const opts = { method, headers }
  if (body !== undefined) opts.body = JSON.stringify(body)

  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}

export const fetchProducts = (params = {}) => {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  if (params.max_price != null) qs.set('max_price', params.max_price)
  const query = qs.toString() ? `?${qs}` : ''
  return request('GET', `/api/products${query}`)
}

export const fetchProduct = (id) => request('GET', `/api/products/${id}`)

export const register = (data) => request('POST', '/auth/register', data)
export const login = (data) => request('POST', '/auth/login', data)

export const fetchPurchases = (customerId) =>
  request('GET', `/api/purchases/${customerId}`)

let _rpcSeq = 0

export async function a2aRpc(messageText) {
  const id = `rpc-${++_rpcSeq}-${Date.now()}`
  const messageId = `msg-${Date.now()}`

  const headers = {
    'Content-Type': 'application/json',
    'A2A-Version': '1.0',
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const envelope = {
    jsonrpc: '2.0',
    id,
    method: 'SendMessage',
    params: {
      message: {
        role: 'ROLE_USER',
        parts: [{ text: messageText }],
        messageId,
      },
    },
  }

  const res = await fetch('/rpc', {
    method: 'POST',
    headers,
    body: JSON.stringify(envelope),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`RPC ${res.status}: ${text}`)
  }

  const json = await res.json()
  if (json.error) throw new Error(json.error.message ?? JSON.stringify(json.error))
  return json.result
}
