import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import StatCard from '../components/StatCard'
import StatusBanner from '../components/StatusBanner'
import TableCard from '../components/TableCard'
import { analyzePortfolio, fetchTickerPrice } from '../lib/api'

const PORTFOLIO_STORAGE_KEY = 'steward_quant_portfolio_holdings'

const scriptOptions = [
  'RELIANCE.NS',
  'TCS.NS',
  'HDFCBANK.NS',
  'INFY.NS',
  'ICICIBANK.NS',
  'SBIN.NS',
  'ITC.NS',
  'LT.NS',
  'AXISBANK.NS',
  'KOTAKBANK.NS',
]

const asMoney = (value) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value || 0)

function pnlClass(value) {
  if (value > 0) return 'pnl-positive'
  if (value < 0) return 'pnl-negative'
  return 'pnl-neutral'
}

function recClass(value) {
  const recommendation = String(value || 'HOLD').toLowerCase()
  return `rec-chip rec-${recommendation}`
}

function PortfolioPage() {
  const [selectedTicker, setSelectedTicker] = useState(scriptOptions[0])
  const [quantity, setQuantity] = useState('')
  const [avgPrice, setAvgPrice] = useState('')
  const [marketPrice, setMarketPrice] = useState(null)
  const [quoteStatus, setQuoteStatus] = useState('Loading latest price...')
  const [holdings, setHoldings] = useState([])
  const [status, setStatus] = useState('Create portfolio by selecting script, quantity, and average price.')
  const [statusTone, setStatusTone] = useState('neutral')
  const [portfolio, setPortfolio] = useState(null)

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(PORTFOLIO_STORAGE_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return
      const cleaned = parsed.filter(
        (row) => row && typeof row.ticker === 'string' && Number(row.quantity) > 0 && Number(row.avg_price) >= 0,
      )
      if (cleaned.length > 0) {
        setHoldings(
          cleaned.map((row) => ({
            ticker: row.ticker,
            quantity: Number(row.quantity),
            avg_price: Number(row.avg_price),
          })),
        )
        setStatus('Saved portfolio loaded from local storage.')
        setStatusTone('success')
      }
    } catch {
      setStatus('Could not load saved portfolio.')
      setStatusTone('warning')
    }
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem(PORTFOLIO_STORAGE_KEY, JSON.stringify(holdings))
    } catch {
      // Ignore storage quota/privacy errors and keep app functional.
    }
  }, [holdings])

  useEffect(() => {
    let active = true
    const loadQuote = async () => {
      setQuoteStatus('Loading latest price...')
      try {
        const price = await fetchTickerPrice(selectedTicker)
        if (!active) return
        if (price) {
          setMarketPrice(Number(price))
          setQuoteStatus('Advisory market price based on latest fetched close.')
        } else {
          setMarketPrice(null)
          setQuoteStatus('Market price unavailable right now.')
        }
      } catch {
        if (!active) return
        setMarketPrice(null)
        setQuoteStatus('Failed to fetch market price.')
      }
    }
    loadQuote()
    return () => {
      active = false
    }
  }, [selectedTicker])

  const addHolding = () => {
    const qty = Number(quantity)
    const avg = Number(avgPrice)
    if (!selectedTicker || qty <= 0 || Number.isNaN(qty) || avg < 0 || Number.isNaN(avg)) {
      setStatus('Invalid input. Select script and enter valid quantity (>0) and average price (>=0).')
      setStatusTone('warning')
      return
    }

    setHoldings((prev) => {
      const existing = prev.find((row) => row.ticker === selectedTicker)
      if (existing) {
        return prev.map((row) =>
          row.ticker === selectedTicker ? { ...row, quantity: qty, avg_price: avg } : row,
        )
      }
      return [...prev, { ticker: selectedTicker, quantity: qty, avg_price: avg }]
    })
    setQuantity('')
    setAvgPrice('')
    setStatus(`Added ${selectedTicker} to portfolio holdings.`)
    setStatusTone('success')
  }

  const removeHolding = (ticker) => {
    setHoldings((prev) => prev.filter((row) => row.ticker !== ticker))
  }

  const savePortfolio = () => {
    if (holdings.length === 0) {
      setStatus('No holdings to save. Add holdings first.')
      setStatusTone('warning')
      return
    }
    try {
      window.localStorage.setItem(PORTFOLIO_STORAGE_KEY, JSON.stringify(holdings))
      setStatus('Portfolio saved locally in this browser.')
      setStatusTone('success')
    } catch {
      setStatus('Failed to save portfolio locally.')
      setStatusTone('error')
    }
  }

  const clearPortfolio = () => {
    setHoldings([])
    setPortfolio(null)
    try {
      window.localStorage.removeItem(PORTFOLIO_STORAGE_KEY)
    } catch {
      // Ignore storage errors.
    }
    setStatus('Portfolio cleared.')
    setStatusTone('neutral')
  }

  const runAnalysis = async () => {
    if (holdings.length === 0) {
      setStatus('Please add at least one holding first.')
      setStatusTone('warning')
      return
    }
    setStatus('Analyzing portfolio...')
    setStatusTone('neutral')
    try {
      const data = await analyzePortfolio(holdings)
      setPortfolio(data.portfolio || null)
      setStatus(`Portfolio analysis updated at ${new Date().toLocaleTimeString()}`)
      setStatusTone('success')
    } catch (error) {
      setStatus(`Portfolio analysis failed: ${error.message}`)
      setStatusTone('error')
    }
  }

  const summary = portfolio?.summary || {}
  const positions = portfolio?.positions || []

  const builderRows = useMemo(
    () =>
      holdings.map((row) => [
        row.ticker,
        row.quantity,
        row.avg_price,
        <button type="button" className="btn-mini danger" onClick={() => removeHolding(row.ticker)}>
          Remove
        </button>,
      ]),
    [holdings],
  )

  const positionRows = positions.map((position) => {
    const recommendation = position.recommendation || 'HOLD'
    return [
      position.ticker,
      position.quantity,
      position.avg_price,
      position.current_price,
      asMoney(position.current_value),
      <span className={pnlClass(position.unrealized_pnl)}>{asMoney(position.unrealized_pnl)}</span>,
      position.final_score,
      <span className={recClass(recommendation)}>{recommendation}</span>,
    ]
  })

  const allocationChartData = useMemo(
    () =>
      positions.map((position) => ({
        name: position.ticker.replace('.NS', ''),
        value: Number(position.current_value) || 0,
      })),
    [positions],
  )

  const pnlChartData = useMemo(
    () =>
      positions.map((position) => ({
        ticker: position.ticker.replace('.NS', ''),
        pnl: Number(position.unrealized_pnl) || 0,
      })),
    [positions],
  )

  return (
    <div className="page-stack">
      <section className="panel">
        <h2 className="panel-title">Create Portfolio</h2>
        <div className="portfolio-builder-grid">
          <label>
            Script
            <select value={selectedTicker} onChange={(event) => setSelectedTicker(event.target.value)}>
              {scriptOptions.map((ticker) => (
                <option key={ticker} value={ticker}>
                  {ticker}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quantity
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              placeholder="e.g. 20"
            />
          </label>
          <label>
            Avg Price
            <input
              type="number"
              min="0"
              step="0.01"
              value={avgPrice}
              onChange={(event) => setAvgPrice(event.target.value)}
              placeholder="e.g. 2450"
            />
          </label>
          <button type="button" onClick={addHolding}>
            Add Holding
          </button>
        </div>
        <p className="inline-note">
          Current market price advice for <b>{selectedTicker}</b>:&nbsp;
          <span className="quote-pill">{marketPrice ? asMoney(marketPrice) : 'N/A'}</span>
          <span className="muted"> {quoteStatus}</span>
        </p>
        <div className="actions-row">
          <button type="button" onClick={runAnalysis}>
            Analyze Portfolio
          </button>
          <button type="button" className="btn-secondary" onClick={savePortfolio}>
            Save Portfolio
          </button>
          <button type="button" className="btn-secondary danger" onClick={clearPortfolio}>
            Clear
          </button>
        </div>
        <StatusBanner text={status} tone={statusTone} />
      </section>

      <TableCard
        title="Selected Holdings"
        headers={['Ticker', 'Qty', 'Avg Price', 'Action']}
        rows={builderRows}
        emptyText="No holdings added yet. Use the form above."
      />

      <section className="stats-grid">
        <StatCard label="Total Invested" value={asMoney(summary.total_invested || 0)} />
        <StatCard label="Current Value" value={asMoney(summary.total_current_value || 0)} />
        <StatCard
          label="Unrealized PnL"
          value={asMoney(summary.total_unrealized_pnl || 0)}
          valueClass={pnlClass(summary.total_unrealized_pnl || 0)}
        />
        <StatCard
          label="Unrealized PnL %"
          value={`${summary.total_unrealized_pnl_pct ?? 0}%`}
          valueClass={pnlClass(summary.total_unrealized_pnl_pct || 0)}
        />
        <StatCard
          label="Expected PnL 7D"
          value={asMoney(summary.expected_pnl_next_7d || 0)}
          valueClass={pnlClass(summary.expected_pnl_next_7d || 0)}
        />
        <StatCard
          label="Expected PnL 21D"
          value={asMoney(summary.expected_pnl_next_21d || 0)}
          valueClass={pnlClass(summary.expected_pnl_next_21d || 0)}
        />
      </section>

      <section className="chart-grid">
        <article className="panel chart-panel">
          <h3 className="panel-title">Portfolio Allocation</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={allocationChartData} dataKey="value" nameKey="name" outerRadius={95} label>
                  {allocationChartData.map((entry, index) => {
                    const palette = ['#23c28f', '#36a9cd', '#f9a825', '#ff7d7d', '#8a9fff', '#5ed7a3']
                    return <Cell key={`${entry.name}-${index}`} fill={palette[index % palette.length]} />
                  })}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <h3 className="panel-title">PnL by Position</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={pnlChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(154,178,194,0.18)" />
                <XAxis dataKey="ticker" stroke="#9ab2c2" />
                <YAxis stroke="#9ab2c2" />
                <Tooltip />
                <Bar dataKey="pnl" radius={[6, 6, 0, 0]}>
                  {pnlChartData.map((entry, index) => (
                    <Cell key={`pnl-${entry.ticker}-${index}`} fill={entry.pnl < 0 ? '#ff7d7d' : '#23c28f'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <TableCard
        title="Portfolio Positions"
        headers={['Ticker', 'Qty', 'Avg Price', 'Current Price', 'Value', 'PnL', 'Score', 'Recommendation']}
        rows={positionRows}
      />
    </div>
  )
}

export default PortfolioPage
