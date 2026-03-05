import { useEffect, useState } from 'react'
import DashboardPage from './pages/DashboardPage'
import MarketPage from './pages/MarketPage'
import PortfolioPage from './pages/PortfolioPage'
import { clearAuthToken, fetchMe, loginUser, registerUser } from './lib/api'

function App() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [user, setUser] = useState(null)
  const [authMode, setAuthMode] = useState('login') // 'login' or 'register'
  const [authMessage, setAuthMessage] = useState('')

  const [showAuthModal, setShowAuthModal] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const me = await fetchMe()
        setUser(me.user)
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
    setAuthMessage('Authenticating...')
    try {
      const data = await loginUser(email.trim().toLowerCase(), password)
      setUser(data.user)
      setPassword('')
      setShowAuthModal(false)
      setAuthMessage('')
    } catch (error) {
      setAuthMessage(`Login failed: ${error.message}`)
    }
  }

  const handleRegister = async () => {
    if (!email.trim() || !password.trim()) {
      setAuthMessage('Email and password required.')
      return
    }
    setAuthMessage('Creating account...')
    try {
      await registerUser(email.trim().toLowerCase(), password, fullName)
      setAuthMessage('Account created! Please sign in.')
      setAuthMode('login')
      setFullName('')
    } catch (error) {
      setAuthMessage(`Registration failed: ${error.message}`)
    }
  }

  const handleLogout = () => {
    clearAuthToken()
    setUser(null)
  }

  const [activeTab, setActiveTab] = useState('dashboard')

  useEffect(() => {
    const handleScroll = () => {
      const sections = ['dashboard', 'market', 'portfolio']
      const current = sections.find(id => {
        const el = document.getElementById(id)
        if (el) {
          const rect = el.getBoundingClientRect()
          return rect.top >= -100 && rect.top <= 300
        }
        return false
      })
      if (current) setActiveTab(current)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <h1 className="app-title">Steward Quant</h1>
          <p className="app-subtitle">High-Frequency Intelligence</p>
        </div>
        <nav className="onepager-nav">
          <a className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`} href="#dashboard">
            Dashboard
          </a>
          <a className={`nav-link ${activeTab === 'market' ? 'active' : ''}`} href="#market">
            Market Pulse
          </a>
          <a className={`nav-link ${activeTab === 'portfolio' ? 'active' : ''}`} href="#portfolio">
            Portfolio
          </a>
        </nav>
        <div className="header-auth">
          {user ? (
            <div className="user-profile">
              <span className="welcome-pill">STWD_{user.role?.toUpperCase() || 'USER'}</span>
              <span className="user-name">{user.full_name || user.email.split('@')[0]}</span>
              <button type="button" className="btn-secondary danger btn-mini" onClick={handleLogout}>
                Sign Out
              </button>
            </div>
          ) : (
            <button type="button" className="btn-auth-trigger" onClick={() => setShowAuthModal(true)}>
              Sign In
            </button>
          )}
        </div>
      </header>

      {showAuthModal && (
        <div className="auth-overlay">
          <div className="auth-modal">
            <button className="auth-modal-close" onClick={() => setShowAuthModal(false)}>×</button>
            <div className="auth-modal-header">
              <h2 className="auth-modal-title">{authMode === 'login' ? 'Institutional Sign In' : 'Create Credentials'}</h2>
              <p className="auth-modal-desc">{authMode === 'login' ? 'Access your high-frequency terminal' : 'Get started with quantitative intelligence'}</p>
            </div>

            <div className="auth-modal-form">
              {authMessage && <div className="auth-error-msg">{authMessage}</div>}

              {authMode === 'register' && (
                <div className="modal-input-group">
                  <label>Full Name</label>
                  <input
                    className="modal-input"
                    type="text"
                    placeholder="e.g. Selva Kumar"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>
              )}
              <div className="modal-input-group">
                <label>Institutional Email</label>
                <input
                  className="modal-input"
                  type="email"
                  placeholder="name@steward.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="modal-input-group">
                <label>Secure Key</label>
                <input
                  className="modal-input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <button type="button" onClick={authMode === 'login' ? handleLogin : handleRegister}>
                {authMode === 'login' ? 'Access Terminal' : 'Create Credentials'}
              </button>
            </div>

            <div className="auth-modal-footer">
              {authMode === 'login' ? (
                <p>New to Steward? <button onClick={() => { setAuthMode('register'); setAuthMessage(''); }}>Register now</button></p>
              ) : (
                <p>Already have an account? <button onClick={() => { setAuthMode('login'); setAuthMessage(''); }}>Sign in</button></p>
              )}
            </div>
          </div>
        </div>
      )}

      <main className="page-stack">
        <section id="dashboard" className="section-panel">
          <h2 className="section-title">Institutional Overview</h2>
          <DashboardPage user={user} />
        </section>

        <section id="market" className="section-panel">
          <h2 className="section-title">Market Intelligence</h2>
          <MarketPage user={user} />
        </section>

        <section id="portfolio" className="section-panel">
          <h2 className="section-title">Quantitative Portfolio</h2>
          <PortfolioPage user={user} />
        </section>
      </main>
    </div>
  )
}

export default App
