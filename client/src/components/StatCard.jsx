function StatCard({ label, value, valueClass = '', info = '' }) {
  return (
    <article className="stat-card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <p className="stat-label" style={{ marginBottom: 0 }}>{label}</p>
        {info && <span className="info-tip" title={info}>ⓘ</span>}
      </div>
      <p className={`stat-value ${valueClass}`.trim()}>{value}</p>
    </article>
  )
}

export default StatCard
