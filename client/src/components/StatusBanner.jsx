function StatusBanner({ text, tone = 'neutral' }) {
  return <p className={`status-banner status-${tone}`}>{text}</p>
}

export default StatusBanner
