type TopbarProps = {
  title: string
  subtitle?: string
}

function Topbar({ title, subtitle }: TopbarProps) {
  return (
    <header className="dashboard-topbar">
      <div>
        <h1>{title}</h1>

        {subtitle && (
          <p>{subtitle}</p>
        )}
      </div>

      <div className="topbar-system-status">
        <span className="status-dot online" />
        Backend Connected
      </div>
    </header>
  )
}

export default Topbar
