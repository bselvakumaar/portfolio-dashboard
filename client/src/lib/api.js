const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const AUTH_TOKEN_KEY = 'steward_auth_token'

export function getAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAuthToken(token) {
  if (!token) return
  window.localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearAuthToken() {
  window.localStorage.removeItem(AUTH_TOKEN_KEY)
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getAuthToken()
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      // ignore JSON parse failure
    }
    throw new Error(detail)
  }
  return response.json()
}

export function registerUser(email, password, fullName = '') {
  return request('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  })
}

export async function loginUser(email, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (data?.access_token) setAuthToken(data.access_token)
  return data
}

export function fetchMe() {
  return request('/auth/me')
}

export function fetchDashboard(payload) {
  return request('/dashboard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchMarketSnapshot(topN = 10) {
  return request(`/market/snapshot?top_n=${topN}`)
}

export function analyzePortfolio(holdings) {
  return request('/portfolio/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ holdings }),
  })
}

export async function fetchTickerPrice(ticker) {
  const data = await fetchDashboard({
    tickers: [ticker],
    top_n: 1,
    capital: 100000,
    push_to_sheets: false,
  })
  return data?.results?.[0]?.indicators?.close ?? null
}

export function createTradingAccount(initialFunds = 0) {
  return request('/trading/account/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initial_funds: Number(initialFunds) || 0 }),
  })
}

export function getMyTradingAccount() {
  return request('/trading/account/me')
}

export function addTradingFunds(amount) {
  return request('/trading/funds/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount: Number(amount) }),
  })
}

export function placeBuyOrder(ticker, quantity, price) {
  const payload = { ticker, quantity: Number(quantity) }
  if (price !== '' && price !== null && price !== undefined) payload.price = Number(price)
  return request('/trading/order/buy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function placeSellOrder(ticker, quantity, price) {
  const payload = { ticker, quantity: Number(quantity) }
  if (price !== '' && price !== null && price !== undefined) payload.price = Number(price)
  return request('/trading/order/sell', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchAdminTradingOverview() {
  return request('/admin/trading/overview')
}
