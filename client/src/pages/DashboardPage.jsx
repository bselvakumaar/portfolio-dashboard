import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend as RechartsLegend,
  Line,
  LineChart,
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
import TopPickCard from '../components/TopPickCard'
import { fetchDashboard } from '../lib/api'

const defaultTickers = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS']

const asMoney = (value) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

const recColors = {
  strong_buy: '#3ddc97',
  buy: '#23c28f',
  hold: '#f9a825',
  avoid: '#ff7d7d',
}

function DashboardPage({ user }) {
  const [tickers, setTickers] = useState(defaultTickers.join(','))
  const [topN, setTopN] = useState(5)
  const [capital, setCapital] = useState(1000000)
  const [status, setStatus] = useState('Ready.')
  const [statusTone, setStatusTone] = useState('neutral')
  const [data, setData] = useState(null)

  const runDashboard = async () => {
    setStatus('Running dashboard...')
    setStatusTone('neutral')
    try {
      const payload = {
        tickers: tickers.split(',').map((item) => item.trim()).filter(Boolean),
        top_n: Math.max(1, Math.min(20, Number(topN) || 5)),
        capital: Math.max(1, Number(capital) || 1000000),
        push_to_sheets: false,
      }
      const dashboard = await fetchDashboard(payload)
      setData(dashboard)
      setStatus(`Dashboard updated at ${new Date().toLocaleTimeString()}`)
      setStatusTone('success')
    } catch (error) {
      setStatus(`Dashboard failed: ${error.message}`)
      setStatusTone('error')
    }
  }

  useEffect(() => {
    if (user && !data) {
      runDashboard()
    }
  }, [user, data])

  const overview = data?.market_overview || {}
  const topPicks = data?.top_picks || []
  const syntheticPositions = data?.synthetic_portfolio?.positions || []
  const syntheticSummary = data?.synthetic_portfolio?.summary || {}

  const portfolioRows = useMemo(
    () =>
      syntheticPositions.map((position) => [
        position.ticker,
        `${((position.weight || 0) * 100).toFixed(2)}%`,
        asMoney(position.allocation),
        `${position.predicted_return_21d_pct ?? 0}%`,
        position.recommendation || 'HOLD',
      ]),
    [syntheticPositions],
  )

  const picksChartData = useMemo(
    () =>
      topPicks.map((pick) => ({
        ticker: pick.ticker.replace('.NS', ''),
        ret21d:
          Number(
            pick?.prediction?.projection?.next_21d_return_pct ?? pick?.prediction?.predicted_return_pct ?? 0,
          ) || 0,
        confidence: Number(pick?.prediction?.confidence ?? 0) || 0,
      })),
    [topPicks],
  )

  const recMixData = useMemo(() => {
    const counts = topPicks.reduce((acc, pick) => {
      const rec = String(pick?.prediction?.recommendation || 'hold').toLowerCase()
      acc[rec] = (acc[rec] || 0) + 1
      return acc
    }, {})
    return Object.entries(counts).map(([name, value]) => ({ name: name.toUpperCase(), key: name, value }))
  }, [topPicks])

  if (!user) {
    return (
      <div className="page-stack">
        <section className="panel" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div className="lock-icon" style={{ fontSize: '48px', marginBottom: '24px' }}>🔒</div>
          <h2 className="panel-title" style={{ marginBottom: '12px' }}>Institutional Research Locked</h2>
          <p className="muted" style={{ maxWidth: '400px', textAlign: 'center', marginBottom: '32px' }}>
            Detailed quantitative analysis and alpha signals are restricted to verified accounts.
            Please login to access live research and prediction models.
          </p>
          <div className="stats-grid" style={{ opacity: 0.3, filter: 'blur(4px)', pointerEvents: 'none', width: '100%' }}>
            <StatCard label="Total Coverage" value="--" />
            <StatCard label="Verified Tickers" value="--" />
            <StatCard label="Quant Score" value="--" />
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <h2 className="panel-title">System Configuration</h2>
        <div className="controls-grid">
          <label>
            Market Tickers
            <input
              value={tickers}
              onChange={(event) => setTickers(event.target.value)}
              placeholder="RELIANCE.NS, TCS.NS..."
            />
          </label>
          <label>
            Target Picks
            <input
              type="number"
              min="1"
              max="20"
              value={topN}
              onChange={(event) => setTopN(event.target.value)}
            />
          </label>
          <label>
            AUM Capital (INR)
            <input
              type="number"
              min="1"
              value={capital}
              onChange={(event) => setCapital(event.target.value)}
            />
          </label>
          <button type="button" onClick={runDashboard}>
            Execute Research
          </button>
        </div>
        <StatusBanner text={status} tone={statusTone} />
      </section>

      <div className="stats-grid">
        <StatCard label="Total Coverage" value={overview.coverage_tickers ?? '--'} />
        <StatCard label="Verified Tickers" value={overview.valid_tickers ?? '--'} />
        <StatCard label="Quant Score" value={overview.average_steward_score ?? '0.00'} />
        <StatCard label="Pred Action (21D)" value={`${overview.average_predicted_return_21d_pct ?? '0'}%`} />
        <StatCard label="Expected PnL" value={asMoney(syntheticSummary.expected_pnl_21d || 0)} />
        <StatCard label="Diversification" value={syntheticSummary.diversification_index ?? '0.00'} />
      </div>

      <section>
        <h3 className="section-title">Institutional Alpha Picks</h3>
        <div className="pick-grid">
          {topPicks.length === 0 ? (
            <div className="panel"><p className="muted">Pending alpha signals...</p></div>
          ) : (
            topPicks.map((pick) => <TopPickCard key={pick.ticker} pick={pick} />)
          )}
        </div>
      </section>

      <section className="chart-grid">
        <article className="panel chart-panel">
          <h3 className="panel-title">Market Dynamics</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={picksChartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={1} />
                    <stop offset="100%" stopColor="var(--accent-glow)" stopOpacity={0.8} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="ticker"
                  stroke="var(--text-muted)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  dy={10}
                />
                <YAxis
                  yAxisId="left"
                  stroke="var(--text-muted)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="var(--text-muted)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-surface)',
                    borderColor: 'var(--border-subtle)',
                    borderRadius: '8px',
                    boxShadow: 'var(--shadow-lg)'
                  }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <RechartsLegend iconType="circle" />
                <Bar
                  yAxisId="left"
                  dataKey="ret21d"
                  name="Pred 21D %"
                  fill="url(#barGradient)"
                  radius={[4, 4, 0, 0]}
                  barSize={32}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="confidence"
                  name="Confidence"
                  stroke="var(--success)"
                  strokeWidth={3}
                  dot={{ r: 4, fill: 'var(--success)', strokeWidth: 2, stroke: 'var(--bg-surface)' }}
                  activeDot={{ r: 6 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <h3 className="panel-title">Recommendation Analysis</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={recMixData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  stroke="none"
                >
                  {recMixData.map((entry) => (
                    <Cell key={entry.name} fill={recColors[entry.key] || 'var(--text-muted)'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-surface)',
                    borderColor: 'var(--border-subtle)',
                    borderRadius: '8px'
                  }}
                />
                <RechartsLegend verticalAlign="bottom" iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <TableCard
        title="Synthetic Portfolio"
        headers={['Ticker', 'Weight', 'Allocation', 'Pred 21D', 'Recommendation']}
        rows={portfolioRows}
      />
    </div>
  )
}

export default DashboardPage
