import DashboardPage from './pages/DashboardPage'
import MarketPage from './pages/MarketPage'
import PortfolioPage from './pages/PortfolioPage'

function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1 className="app-title">Steward Quant Client</h1>
          <p className="app-subtitle">Simple one-page dashboard for market and portfolio management.</p>
        </div>
        <nav className="topnav onepager-nav">
          <a className="nav-link" href="#dashboard">
            Dashboard
          </a>
          <a className="nav-link" href="#market">
            Market Pulse
          </a>
          <a className="nav-link" href="#portfolio">
            Portfolio
          </a>
        </nav>
      </header>

      <main className="page-stack">
        <section id="dashboard" className="section-panel">
          <h2 className="section-title">Dashboard</h2>
          <DashboardPage />
        </section>

        <section id="market" className="section-panel">
          <h2 className="section-title">Market Pulse</h2>
          <MarketPage />
        </section>

        <section id="portfolio" className="section-panel">
          <h2 className="section-title">Portfolio</h2>
          <PortfolioPage />
        </section>
      </main>
    </div>
  )
}

export default App
