function TopPickCard({ pick }) {
  const recommendation = pick?.prediction?.recommendation || 'HOLD'
  const recClass = `rec-chip rec-${String(recommendation).toLowerCase()}`
  return (
    <article className="pick-card">
      <p className="pick-ticker">{pick.ticker}</p>
      <p>Score: <b>{pick.final_score}</b></p>
      <p>Pred 21D: <b>{pick?.prediction?.predicted_return_pct ?? 0}%</b></p>
      <p>Confidence: <b>{pick?.prediction?.confidence ?? 0}</b></p>
      <span className={recClass}>{recommendation}</span>
    </article>
  )
}

export default TopPickCard
