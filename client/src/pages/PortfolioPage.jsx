import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend as RechartsLegend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import StatCard from '../components/StatCard'
import StatusBanner from '../components/StatusBanner'
import TableCard from '../components/TableCard'
import {
  addTradingFunds,
  analyzePortfolio,
  clearAuthToken,
  createTradingAccount,
  fetchAdminTradingOverview,
  fetchMe,
  fetchTickerPrice,
  getMyTradingAccount,
  loginUser,
  placeBuyOrder,
  placeSellOrder,
  registerUser,
} from '../lib/api'

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

function InfoTip({ text }) {
  return (
    <span className="info-tip" title={text}>ⓘ</span>
  )
}

const CHART_COLORS = ['#38bdf8', '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#a78bfa']

function WorkflowMap({ activeStep }) {
  return (
    <section className="panel workflow-panel">
      <div className="workflow-steps">
        <div className={`step-item ${activeStep >= 1 ? 'active' : ''}`}>
          <div className="step-num">1</div>
          <div className="step-body">
            <h4 className="step-title">Select Assets</h4>
            <p className="step-desc">Build your institutional draft list.</p>
          </div>
        </div>
        <div className="step-arrow">→</div>
        <div className={`step-item ${activeStep >= 2 ? 'active' : ''}`}>
          <div className="step-num">2</div>
          <div className="step-body">
            <h4 className="step-title">Quant Compute</h4>
            <p className="step-desc">Execute high-frequency math models.</p>
          </div>
        </div>
        <div className="step-arrow">→</div>
        <div className={`step-item ${activeStep >= 3 ? 'active' : ''}`}>
          <div className="step-num">3</div>
          <div className="step-body">
            <h4 className="step-title">Strategy Review</h4>
            <p className="step-desc">Finalize and analyze alpha scores.</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function PortfolioPage({ user }) {
  const [selectedTicker, setSelectedTicker] = useState(scriptOptions[0])
  const [isOutOfSync, setIsOutOfSync] = useState(false)
  const [quantity, setQuantity] = useState('')
  const [avgPrice, setAvgPrice] = useState('')
  const [marketPrice, setMarketPrice] = useState(null)
  const [quoteStatus, setQuoteStatus] = useState('Loading latest price...')
  const [holdings, setHoldings] = useState([])
  const [status, setStatus] = useState('Create portfolio by selecting script, quantity, and average price.')
  const [statusTone, setStatusTone] = useState('neutral')
  const [portfolio, setPortfolio] = useState(null)
  const [tradeFundAmount, setTradeFundAmount] = useState('')
  const [tradeQty, setTradeQty] = useState('')
  const [tradePrice, setTradePrice] = useState('')
  const [tradeTicker, setTradeTicker] = useState(scriptOptions[0])
  const [tradeStatus, setTradeStatus] = useState('Please login to access trading account.')
  const [tradeStatusTone, setTradeStatusTone] = useState('neutral')
  const [tradeAccount, setTradeAccount] = useState(null)
  const [adminOverview, setAdminOverview] = useState(null)
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authName, setAuthName] = useState('')
  const [authStatus, setAuthStatus] = useState('Login/Register to access your own trading account.')
  const [authTone, setAuthTone] = useState('neutral')
  // We use the 'user' prop passed from App.jsx instead of local currentUser state

  const isSuperadmin = user?.role === 'superadmin'
  const isLoggedIn = Boolean(user?.email)

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
      // ignore storage errors
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

  useEffect(() => {
    const boot = async () => {
      if (!user) {
        setTradeAccount(null)
        setAdminOverview(null)
        return
      }
      try {
        if (user.role === 'superadmin') {
          const overview = await fetchAdminTradingOverview()
          setAdminOverview(overview)
          setTradeStatus('Superadmin has read-only global visibility.')
          setTradeStatusTone('neutral')
        } else {
          await createTradingAccount(0)
          const acc = await getMyTradingAccount()
          setTradeAccount(acc)
          setTradeStatus('Trading account loaded.')
          setTradeStatusTone('success')
        }
      } catch (error) {
        setTradeStatus(`Failed to load trading data: ${error.message}`)
        setTradeStatusTone('error')
      }
    }
    boot()
  }, [user])

  const refreshTradingAccount = async () => {
    try {
      if (isSuperadmin) {
        const overview = await fetchAdminTradingOverview()
        setAdminOverview(overview)
      } else {
        const account = await getMyTradingAccount()
        setTradeAccount(account)
      }
      setTradeStatus('Refreshed successfully.')
      setTradeStatusTone('success')
    } catch (error) {
      setTradeStatus(`Refresh failed: ${error.message}`)
      setTradeStatusTone('error')
    }
  }

  const handleAddFunds = async () => {
    const amount = Number(tradeFundAmount)
    if (!amount || amount <= 0) {
      setTradeStatus('Enter valid fund amount (>0).')
      setTradeStatusTone('warning')
      return
    }
    try {
      const account = await addTradingFunds(amount)
      setTradeAccount(account)
      setTradeFundAmount('')
      setTradeStatus('Funds added successfully.')
      setTradeStatusTone('success')
    } catch (error) {
      setTradeStatus(`Add funds failed: ${error.message}`)
      setTradeStatusTone('error')
    }
  }

  const handleBuySell = async (side) => {
    const qty = Number(tradeQty)
    if (!tradeTicker || !qty || qty <= 0) {
      setTradeStatus('Enter valid ticker and quantity (>0).')
      setTradeStatusTone('warning')
      return
    }
    try {
      const account =
        side === 'buy'
          ? await placeBuyOrder(tradeTicker, qty, tradePrice)
          : await placeSellOrder(tradeTicker, qty, tradePrice)
      setTradeAccount(account)
      setTradeStatus(`${side.toUpperCase()} order executed.`)
      setTradeStatusTone('success')
      setTradeQty('')
      setTradePrice('')
    } catch (error) {
      setTradeStatus(`${side.toUpperCase()} failed: ${error.message}`)
      setTradeStatusTone('error')
    }
  }

  const removeHolding = (ticker) => {
    setHoldings((prev) => prev.filter((row) => row.ticker !== ticker))
    setIsOutOfSync(true)
  }

  const savePortfolio = () => {
    if (holdings.length === 0) {
      setStatus('No holdings to save. Add holdings first.')
      setStatusTone('warning')
      return
    }
    window.localStorage.setItem(PORTFOLIO_STORAGE_KEY, JSON.stringify(holdings))
    setStatus('Portfolio saved locally in this browser.')
    setStatusTone('success')
  }

  const clearPortfolio = () => {
    setHoldings([])
    setPortfolio(null)
    window.localStorage.removeItem(PORTFOLIO_STORAGE_KEY)
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
      setIsOutOfSync(false)
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
      holdings.map((row, index) => [
        <div key={`builder-${row.ticker}`} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
            display: 'inline-block',
            boxShadow: '0 0 8px var(--accent-glow)'
          }} />
          <span style={{ fontWeight: 700 }}>{row.ticker}</span>
        </div>,
        row.quantity,
        asMoney(row.avg_price),
        <button type="button" className="btn-mini danger" onClick={() => removeHolding(row.ticker)}>
          Remove
        </button>,
      ]),
    [holdings],
  )

  const positionRows = positions.map((position, index) => {
    const recommendation = position.recommendation || 'HOLD'
    return [
      <div key={`pos-${position.ticker}`} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{
          width: '10px',
          height: '10px',
          borderRadius: '50%',
          backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
          display: 'inline-block'
        }} />
        <span style={{ fontWeight: 700 }}>{position.ticker}</span>
      </div>,
      position.quantity,
      asMoney(position.avg_price),
      asMoney(position.current_price),
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

  const tradeHoldingsRows = (tradeAccount?.holdings || []).map((row) => [row.ticker, row.quantity, row.avg_price])
  const transactionRows = (tradeAccount?.transactions || [])
    .slice()
    .reverse()
    .slice(0, 20)
    .map((txn) => [
      txn.time_utc,
      txn.type,
      txn.ticker || '-',
      txn.quantity ?? '-',
      txn.price ?? '-',
      txn.amount ?? txn.net_credit ?? txn.total_debit ?? '-',
      txn.charges ?? '-',
    ])
  const adminRows = (adminOverview?.users || []).map((u) => [
    u.user_id,
    asMoney(u.cash_balance),
    u.holdings_count,
    u.transaction_count,
  ])

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
        return prev.map((row) => (row.ticker === selectedTicker ? { ...row, quantity: qty, avg_price: avg } : row))
      }
      return [...prev, { ticker: selectedTicker, quantity: qty, avg_price: avg }]
    })
    setIsOutOfSync(true)
    setQuantity('')
    setAvgPrice('')
    setStatus(`Added ${selectedTicker} to portfolio holdings.`)
    setStatusTone('success')
  }

  const loadSampleStrategy = () => {
    const sample = [
      { ticker: 'RELIANCE.NS', quantity: 100, avg_price: 2450 },
      { ticker: 'TCS.NS', quantity: 50, avg_price: 3200 },
      { ticker: 'HDFCBANK.NS', quantity: 150, avg_price: 1550 },
    ]
    setHoldings(sample)
    setIsOutOfSync(true)
    setStatus('Institutional sample strategy loaded. Run analysis to see quant scores.')
    setStatusTone('success')
  }

  if (!user) {
    return (
      <div className="page-stack">
        <section className="panel" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div className="lock-icon" style={{ fontSize: '48px', marginBottom: '24px' }}>💼</div>
          <h2 className="panel-title" style={{ marginBottom: '12px' }}>Quantitative Portfolio Locked</h2>
          <p className="muted" style={{ maxWidth: '400px', textAlign: 'center', marginBottom: '32px' }}>
            Portfolio tracking, strategy backtesting, and live trading execution are restricted to authorized accounts.
            Please login to manage your institutional assets.
          </p>
        </section>
      </div>
    )
  }

  return (
    <div className="page-stack">
      <WorkflowMap activeStep={portfolio ? (isOutOfSync ? 1 : 3) : 1} />

      <section className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 className="panel-title" style={{ marginBottom: 0 }}>Step 1: Individual Asset Configuration</h2>
          <span className="welcome-pill">Builder Cockpit</span>
        </div>
        <div className="portfolio-builder-grid">
          <label>
            Asset Script
            <select value={selectedTicker} onChange={(event) => setSelectedTicker(event.target.value)}>
              {scriptOptions.map((ticker) => (
                <option key={ticker} value={ticker}>{ticker}</option>
              ))}
            </select>
          </label>
          <label>
            Holding Quantity
            <input type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="e.g. 100" />
          </label>
          <label>
            Entry Price (Avg)
            <input type="number" min="0" step="0.01" value={avgPrice} onChange={(event) => setAvgPrice(event.target.value)} placeholder="e.g. 150.25" />
          </label>
          <button type="button" onClick={addHolding}>Commit Holding</button>
        </div>
        <p className="inline-note" style={{ marginTop: '20px', fontSize: '12px' }}>
          Current Reference for <b>{selectedTicker}</b>: <span className="welcome-pill">{marketPrice ? asMoney(marketPrice) : 'Fetching...'}</span>
          <span className="muted" style={{ marginLeft: '12px', opacity: 0.7 }}> {quoteStatus}</span>
        </p>
        <div className="actions-row" style={{ marginTop: '24px' }}>
          <button type="button" onClick={runAnalysis} className={isOutOfSync || !portfolio ? 'pulse' : ''}>
            {isOutOfSync ? 'Refresh Quant Analysis' : 'Run Quant Analysis'}
          </button>
          {isSuperadmin && <button type="button" className="btn-secondary" onClick={loadSampleStrategy}>Load Sample Strategy</button>}
          <button type="button" className="btn-secondary" onClick={savePortfolio}>Save Layout</button>
          <button type="button" className="btn-secondary danger" onClick={clearPortfolio}>Reset</button>
        </div>
        <StatusBanner text={status} tone={statusTone} />
      </section>

      <TableCard
        title="Live Selection & Strategy Composition"
        headers={['Asset (Chart Legend)', 'Build Quantity', 'Avg Purchase Price', 'Action']}
        rows={builderRows}
        emptyText="Strategy builder is empty. Add scripts or load sample above."
      />

      {portfolio && isOutOfSync && (
        <div className="status-banner status-error" style={{ marginBottom: '24px', textAlign: 'center' }}>
          ⚠️ <b>OUT OF SYNC:</b> Your strategy selection has changed. Please click <b>Refresh Quant Analysis</b> to update your charts.
        </div>
      )}

      {portfolio ? (
        <>
          <div className="stats-grid">
            <StatCard label="Net Investment" value={asMoney(summary.total_invested || 0)} />
            <StatCard label="Current Valuation" value={asMoney(summary.total_current_value || 0)} />
            <StatCard label="Total Unrealized PnL" value={asMoney(summary.total_unrealized_pnl || 0)} valueClass={pnlClass(summary.total_unrealized_pnl || 0)} />
            <StatCard label="PnL Yield (%)" value={`${summary.total_unrealized_pnl_pct ?? 0}%`} valueClass={pnlClass(summary.total_unrealized_pnl_pct || 0)} />
            <StatCard label="Sigma Pred (7D)" value={asMoney(summary.expected_pnl_next_7d || 0)} valueClass={pnlClass(summary.expected_pnl_next_7d || 0)} info="High-frequency prediction of portfolio volatility/risk over the next week." />
            <StatCard label="Alpha Pred (21D)" value={asMoney(summary.expected_pnl_next_21d || 0)} valueClass={pnlClass(summary.expected_pnl_next_21d || 0)} info="Calculated estimate of excess return (above benchmark) over 3 trading weeks." />
          </div>

          <section className="chart-grid">
            <article className="panel chart-panel">
              <h3 className="panel-title">Portfolio Allocation</h3>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie
                      data={allocationChartData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      stroke="none"
                    >
                      {allocationChartData.map((entry, index) => (
                        <Cell key={`alloc-${entry.name}-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--bg-surface)',
                        borderColor: 'var(--border-subtle)',
                        borderRadius: '8px'
                      }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                    />
                    <RechartsLegend iconType="circle" />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="panel chart-panel">
              <h3 className="panel-title">PnL by Position</h3>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={pnlChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis
                      dataKey="ticker"
                      stroke="var(--text-muted)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="var(--text-muted)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--bg-surface)',
                        borderColor: 'var(--border-subtle)',
                        borderRadius: '8px'
                      }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                    />
                    <Bar dataKey="pnl" radius={[4, 4, 0, 0]} barSize={40}>
                      {pnlChartData.map((entry, index) => (
                        <Cell key={`pnl-bar-${entry.ticker}-${index}`} fill={entry.pnl < 0 ? 'var(--error)' : 'var(--success)'} />
                      ))}
                    </Bar>
                    <RechartsLegend verticalAlign="top" iconType="circle" height={36} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>
          </section>

          <TableCard title="Portfolio Positions" headers={['Ticker', 'Qty', 'Avg Price', 'Current Price', 'Value', 'PnL', 'Score', 'Recommendation']} rows={positionRows} />
        </>
      ) : (
        holdings.length > 0 && (
          <div className="panel" style={{ textAlign: 'center', padding: '40px' }}>
            <p className="muted">Portfolio configuration updated. Click <b>"Run Quant Analysis"</b> to generate performance insight.</p>
          </div>
        )
      )}

      <section className="panel">
        <h2 className="panel-title">Institutional Trading Overview</h2>
        {isSuperadmin ? (
          <>
            <StatusBanner text="Global Portfolio Visibility Active." tone="success" />
            <div className="actions-row">
              <button type="button" className="btn-secondary" onClick={refreshTradingAccount}>Refresh Global Data</button>
            </div>
            <TableCard
              title={`System Users (${adminOverview?.total_users ?? 0})`}
              headers={['User ID', 'Available Cash', 'Assigned Assets', 'Net Trades']}
              rows={adminRows}
              emptyText="No institutional users active."
            />
          </>
        ) : (
          <div className="trading-account-sub">
            <div className="actions-row">
              <button type="button" className="btn-secondary" onClick={refreshTradingAccount}>Refresh Balance</button>
            </div>
            <div className="trading-grid">
              <label>
                Fund Account (INR)
                <input type="number" min="1" value={tradeFundAmount} onChange={(event) => setTradeFundAmount(event.target.value)} placeholder="Deposit amount" />
              </label>
              <button type="button" onClick={handleAddFunds}>Deposit Funds</button>
            </div>
            <div className="portfolio-builder-grid">
              <label>
                Asset
                <select value={tradeTicker} onChange={(event) => setTradeTicker(event.target.value)}>
                  {scriptOptions.map((ticker) => (
                    <option key={`trade-${ticker}`} value={ticker}>{ticker}</option>
                  ))}
                </select>
              </label>
              <label>
                Qty
                <input type="number" min="1" value={tradeQty} onChange={(event) => setTradeQty(event.target.value)} />
              </label>
              <div className="actions-row">
                <button type="button" onClick={() => handleBuySell('buy')}>Execute Buy</button>
                <button type="button" className="btn-secondary" onClick={() => handleBuySell('sell')}>Execute Sell</button>
              </div>
            </div>
            <div className="stats-grid compact-stats">
              <StatCard label="Cash Balance" value={asMoney(tradeAccount?.cash_balance || 0)} />
              <StatCard label="Holdings" value={tradeAccount?.holdings_count ?? 0} />
              <StatCard label="Transactions" value={tradeAccount?.transaction_count ?? 0} />
            </div>
            <StatusBanner text={tradeStatus} tone={tradeStatusTone} />
          </div>
        )}
      </section>


    </div >
  )
}

export default PortfolioPage
