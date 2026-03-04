const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
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
