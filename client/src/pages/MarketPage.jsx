import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import StatusBanner from '../components/StatusBanner'
import TableCard from '../components/TableCard'
import { fetchMarketSnapshot } from '../lib/api'

function MarketPage() {
  const [topN, setTopN] = useState(10)
  const [status, setStatus] = useState('Ready.')
  const [statusTone, setStatusTone] = useState('neutral')
  const [data, setData] = useState(null)

  const loadSnapshot = async () => {
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
    loadSnapshot()
  }, [])

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
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={moverChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(154,178,194,0.18)" />
                <XAxis dataKey="ticker" stroke="#9ab2c2" />
                <YAxis stroke="#9ab2c2" />
                <Tooltip />
                <Bar dataKey="dayReturn" fill="#36a9cd" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <h3 className="panel-title">Sector Performance</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={sectorChartData} layout="vertical" margin={{ top: 10, right: 20, left: 25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(154,178,194,0.18)" />
                <XAxis type="number" stroke="#9ab2c2" />
                <YAxis dataKey="sector" type="category" width={80} stroke="#9ab2c2" />
                <Tooltip />
                <Bar dataKey="avgDay" fill="#23c28f" radius={[0, 6, 6, 0]} />
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
