import { NavLink } from 'react-router-dom'
import './Sidebar.css'

type SidebarProps = {
  onLogout: () => void
}

const navigation = [
  { path: '/', label: 'Overview', icon: '⌂' },
  { path: '/cameras', label: 'Live Cameras', icon: '◉' },
  { path: '/recordings', label: 'Recordings', icon: '▤' },
  { path: '/tracking', label: 'Tracking', icon: '◎' },
  { path: '/detections', label: 'Detections', icon: '◈' },
  { path: '/events', label: 'Events', icon: '◆' },
  { path: '/alerts', label: 'Alerts', icon: '!' },
  { path: '/persons', label: 'Persons', icon: '●' },
  { path: '/vehicles', label: 'Vehicles', icon: '▣' },
]

function Sidebar({ onLogout }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">AX</div>

        <div>
          <div className="sidebar-brand-title">AKS VisionX</div>
          <div className="sidebar-brand-subtitle">
            AI Surveillance
          </div>
        </div>
      </div>

      <div className="sidebar-section-title">
        MONITORING
      </div>

      <nav className="sidebar-nav">
        {navigation.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-section-title">
          SYSTEM
        </div>

        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? 'active' : ''}`
          }
        >
          <span className="sidebar-icon">⚙</span>
          <span>Settings</span>
        </NavLink>

        <button
          className="sidebar-logout"
          onClick={onLogout}
        >
          <span className="sidebar-icon">↪</span>
          <span>Logout</span>
        </button>
      </div>
    </aside>
  )
}

export default Sidebar


