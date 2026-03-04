import { useEffect, useState } from 'react'
import DashboardPage from './pages/DashboardPage'
import MarketPage from './pages/MarketPage'
import PortfolioPage from './pages/PortfolioPage'
import { clearAuthToken, fetchMe, loginUser } from './lib/api'

function App() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [user, setUser] = useState(null)
  const [authMessage, setAuthMessage] = useState('Login to access your portfolio and trading account.')

  useEffect(() => {
    const load = async () => {
      try {
        const me = await fetchMe()
        setUser(me.user)
        setAuthMessage(`Welcome ${me.user.full_name || me.user.email}`)
      } catch {
        // not logged in
      }
    }
    load()
  }, [])

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setAuthMessage('Enter email and password.')
      return
    }
    try {
      const data = await loginUser(email.trim().toLowerCase(), password)
      setUser(data.user)
      setPassword('')
      setAuthMessage(`Welcome ${data.user.full_name || data.user.email}`)
    } catch (error) {
      setAuthMessage(`Login failed: ${error.message}`)
    }
  }

  const handleLogout = () => {
    clearAuthToken()
    setUser(null)
    setAuthMessage('Logged out. Login again to continue.')
  }

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
        <div className="header-auth">
          {user ? (
            <>
              <span className="welcome-pill">Welcome {user.full_name || user.email}</span>
              <button type="button" className="btn-secondary danger" onClick={handleLogout}>
                Logout
              </button>
              <a className="nav-link" href="#portfolio">
                Create Portfolio
              </a>
            </>
          ) : (
            <>
              <input
                className="header-input"
                type="email"
                placeholder="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                className="header-input"
                type="password"
                placeholder="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button type="button" onClick={handleLogin}>
                Login
              </button>
              <a className="nav-link" href="#portfolio">
                Create Portfolio
              </a>
            </>
          )}
        </div>
        <p className="header-auth-msg">{authMessage}</p>
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
