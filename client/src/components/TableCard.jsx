function TableCard({ title, headers, rows, emptyText = 'No data available.' }) {
  return (
    <section className="panel">
      <h3 className="panel-title">{title}</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={headers.length} className="empty-cell">
                  {emptyText}
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={`${title}-${rowIndex}`}>
                  {row.map((value, colIndex) => (
                    <td key={`${title}-${rowIndex}-${colIndex}`}>{value}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default TableCard
