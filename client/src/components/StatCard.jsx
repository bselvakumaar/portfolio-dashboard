function StatCard({ label, value, valueClass = '' }) {
  return (
    <article className="stat-card">
      <p className="stat-label">{label}</p>
      <p className={`stat-value ${valueClass}`.trim()}>{value}</p>
    </article>
  )
}

export default StatCard
