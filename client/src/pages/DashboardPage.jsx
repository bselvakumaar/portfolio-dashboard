import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
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

function DashboardPage() {
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
    runDashboard()
  }, [])

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

  return (
    <div className="page-stack">
      <section className="panel">
        <h2 className="panel-title">Dashboard Controls</h2>
        <div className="controls-grid">
          <label>
            Tickers
            <input value={tickers} onChange={(event) => setTickers(event.target.value)} />
          </label>
          <label>
            Top Picks
            <input type="number" min="1" max="20" value={topN} onChange={(event) => setTopN(event.target.value)} />
          </label>
          <label>
            Capital (INR)
            <input type="number" min="1" value={capital} onChange={(event) => setCapital(event.target.value)} />
          </label>
          <button type="button" onClick={runDashboard}>
            Run Dashboard
          </button>
        </div>
        <StatusBanner text={status} tone={statusTone} />
      </section>

      <section className="stats-grid">
        <StatCard label="Coverage" value={overview.coverage_tickers ?? '-'} />
        <StatCard label="Valid Tickers" value={overview.valid_tickers ?? '-'} />
        <StatCard label="Average Score" value={overview.average_steward_score ?? '-'} />
        <StatCard label="Average Pred 21D" value={`${overview.average_predicted_return_21d_pct ?? '-'}%`} />
        <StatCard label="Expected PnL 21D" value={asMoney(syntheticSummary.expected_pnl_21d || 0)} />
        <StatCard label="Diversification" value={syntheticSummary.diversification_index ?? '-'} />
      </section>

      <section className="panel">
        <h3 className="panel-title">Top Picks</h3>
        <div className="pick-grid">
          {topPicks.length === 0 ? <p className="muted">No top picks yet.</p> : topPicks.map((pick) => <TopPickCard key={pick.ticker} pick={pick} />)}
        </div>
      </section>

      <section className="chart-grid">
        <article className="panel chart-panel">
          <h3 className="panel-title">Top Picks Return vs Confidence</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={picksChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(154,178,194,0.18)" />
                <XAxis dataKey="ticker" stroke="#9ab2c2" />
                <YAxis yAxisId="left" stroke="#9ab2c2" />
                <YAxis yAxisId="right" orientation="right" stroke="#9ab2c2" />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="ret21d" name="Pred 21D %" fill="#36a9cd" radius={[6, 6, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="confidence" name="Confidence" stroke="#23c28f" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <h3 className="panel-title">Recommendation Mix</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={recMixData} dataKey="value" nameKey="name" outerRadius={95} label>
                  {recMixData.map((entry) => (
                    <Cell key={entry.name} fill={recColors[entry.key] || '#9ab2c2'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
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
