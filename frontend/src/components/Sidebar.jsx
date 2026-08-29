import { NavLink } from 'react-router-dom';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-header-wrap">
          <div className="brand-emblem">🇮🇳</div>
          <div className="brand-text">
            <h1>BEIP</h1>
            <p>Electoral Intelligence</p>
          </div>
        </div>
      </div>

      <div className="sidebar-section-title">Navigation</div>
      
      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">📊</span>
          <span>Overview</span>
        </NavLink>
        <NavLink to="/explorer" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">🔍</span>
          <span>Election Explorer</span>
        </NavLink>
        <NavLink to="/insights" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">💡</span>
          <span>Key Insights</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="data-badge-card">
          <div className="pulse-circle"></div>
          <div>
            <div className="data-badge-text">Postgres Gold Warehouse</div>
            <div className="data-badge-sub">Lok Sabha 2019 · Live</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
