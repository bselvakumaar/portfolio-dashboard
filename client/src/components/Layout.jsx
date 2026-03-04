import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/market', label: 'Market Pulse' },
  { to: '/portfolio', label: 'Portfolio' },
]

function Layout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1 className="app-title">Steward Quant Client</h1>
          <p className="app-subtitle">React dashboard client for analytics and portfolio management.</p>
        </div>
        <nav className="topnav">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className="nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
