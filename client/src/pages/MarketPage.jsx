import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend as RechartsLegend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import StatusBanner from '../components/StatusBanner'
import TableCard from '../components/TableCard'
import { fetchMarketSnapshot } from '../lib/api'

function MarketPage({ user }) {
  const [topN, setTopN] = useState(10)
  const [status, setStatus] = useState('Ready.')
  const [statusTone, setStatusTone] = useState('neutral')
  const [data, setData] = useState(null)

  const loadSnapshot = async () => {
    if (!user) return
    setStatus('Loading market pulse...')
    setStatusTone('neutral')
    try {
      const snapshot = await fetchMarketSnapshot(Math.max(1, Math.min(20, Number(topN) || 10)))
      setData(snapshot)
      setStatus(`Market pulse updated at ${new Date().toLocaleTimeString()}`)
      setStatusTone('success')
    } catch (error) {
      setStatus(`Market pulse failed: ${error.message}`)
      setStatusTone('error')
    }
  }

  useEffect(() => {
    if (user && !data) {
      loadSnapshot()
    }
  }, [user, data])

  const gainersRows = useMemo(
    () => (data?.top_gainers || []).map((row) => [row.ticker, row.sector, row.close, `${row.day_return_pct}%`]),
    [data],
  )
  const losersRows = useMemo(
    () => (data?.top_losers || []).map((row) => [row.ticker, row.sector, row.close, `${row.day_return_pct}%`]),
    [data],
  )
  const sectorRows = useMemo(
    () =>
      (data?.sector_summary || []).map((row) => [row.sector, row.scripts, `${row.avg_day_return_pct}%`, row.total_volume]),
    [data],
  )

  const moverChartData = useMemo(() => {
    const gainers = (data?.top_gainers || []).slice(0, 5).map((row) => ({
      ticker: row.ticker.replace('.NS', ''),
      dayReturn: Number(row.day_return_pct) || 0,
      side: 'Gainer',
    }))
    const losers = (data?.top_losers || []).slice(0, 5).map((row) => ({
      ticker: row.ticker.replace('.NS', ''),
      dayReturn: Number(row.day_return_pct) || 0,
      side: 'Loser',
    }))
    return [...gainers, ...losers]
  }, [data])

  const sectorChartData = useMemo(
    () =>
      (data?.sector_summary || []).slice(0, 8).map((row) => ({
        sector: row.sector,
        avgDay: Number(row.avg_day_return_pct) || 0,
      })),
    [data],
  )

  if (!user) {
    return (
      <div className="page-stack">
        <section className="panel" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div className="lock-icon" style={{ fontSize: '48px', marginBottom: '24px' }}>📡</div>
          <h2 className="panel-title" style={{ marginBottom: '12px' }}>Market Intelligence Locked</h2>
          <p className="muted" style={{ maxWidth: '400px', textAlign: 'center', marginBottom: '32px' }}>
            Real-time market movers and sector performance analysis are reserved for members.
          </p>
        </section>
      </div>
    )
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <h2 className="panel-title">Market Pulse Controls</h2>
        <div className="controls-grid compact">
          <label>
            Top Movers
            <input type="number" min="1" max="20" value={topN} onChange={(event) => setTopN(event.target.value)} />
          </label>
          <button type="button" onClick={loadSnapshot}>
            Load Snapshot
          </button>
        </div>
        <StatusBanner text={status} tone={statusTone} />
      </section>

      <div className="panel-grid">
        <TableCard title="Top Gainers" headers={['Ticker', 'Sector', 'Close', 'Day %']} rows={gainersRows} />
        <TableCard title="Top Losers" headers={['Ticker', 'Sector', 'Close', 'Day %']} rows={losersRows} />
      </div>

      <section className="chart-grid">
        <article className="panel chart-panel">
          <h3 className="panel-title">Top Movers (Daily Return %)</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={moverChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="moverGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={1} />
                    <stop offset="100%" stopColor="var(--success)" stopOpacity={0.8} />
                  </linearGradient>
                </defs>
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
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <RechartsLegend verticalAlign="top" iconType="circle" height={36} />
                <Bar dataKey="dayReturn" name="Day Return %" radius={[4, 4, 0, 0]} barSize={40}>
                  {moverChartData.map((entry, index) => (
                    <Cell key={`mover-${entry.ticker}-${index}`} fill={entry.dayReturn < 0 ? 'var(--error)' : 'var(--success)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <h3 className="panel-title">Sector Performance</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={sectorChartData} layout="vertical" margin={{ top: 10, right: 30, left: 40, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="var(--text-muted)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  dataKey="sector"
                  type="category"
                  width={100}
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
                <RechartsLegend verticalAlign="top" iconType="circle" height={36} />
                <Bar dataKey="avgDay" name="Avg Day Return %" radius={[0, 4, 4, 0]} barSize={20}>
                  {sectorChartData.map((entry, index) => (
                    <Cell key={`sector-${entry.sector}-${index}`} fill={entry.avgDay < 0 ? 'var(--error)' : 'var(--accent)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <TableCard
        title="Sector Summary"
        headers={['Sector', 'Scripts', 'Average Day %', 'Total Volume']}
        rows={sectorRows}
      />
    </div>
  )
}

export default MarketPage
