export default function StatCard({ label, value, sub, icon = '📊', color = 'indigo', chip = 'VERIFIED' }) {
  return (
    <div className={`stat-card ${color}`}>
      <div className="stat-top-row">
        <div className={`stat-icon-bubble ${color}`}>
          {icon}
        </div>
        {chip && <div className="stat-chip">{chip}</div>}
      </div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
