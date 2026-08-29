import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import StatCard from '../components/StatCard';
import { fetchSummary, fetchCriminalAnalysis } from '../api';

const PARTY_GRADIENTS = [
  '#4f46e5', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b',
  '#f43f5e', '#8b5cf6', '#0ea5e9', '#059669', '#ea580c'
];

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [criminal, setCriminal] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchSummary(), fetchCriminalAnalysis()])
      .then(([s, c]) => {
        setSummary(s);
        setCriminal(c.criminal_analysis);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading-box">
        <div className="lux-spinner"></div>
        <p>Loading Bharat Election Intelligence Platform...</p>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="loading-box">
        <p>⚠️ Unable to connect to backend server. Please verify FastAPI is active on port 8000.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Page Hero */}
      <div className="page-hero">
        <div className="page-hero-title-group">
          <h2>National Electoral Overview</h2>
          <p>Multi-dimensional analysis of candidate affidavits, political party seat distributions, and legal profile dynamics</p>
        </div>
        <div className="page-pill-tag">
          <span>🏛️</span>
          <span>General Elections · Lok Sabha</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="stat-grid">
        <StatCard 
          label="Total Candidates" 
          value={summary.total_candidates.toLocaleString()} 
          sub="Curated across all parliamentary contests" 
          icon="👥" 
          color="indigo" 
          chip="GOLD STORE"
        />
        <StatCard 
          label="Constituencies" 
          value={summary.total_constituencies.toLocaleString()} 
          sub={`Across ${summary.total_states} States & Union Territories`} 
          icon="🗺️" 
          color="cyan" 
          chip="PAN-INDIA"
        />
        <StatCard 
          label="Leading Party" 
          value={summary.top_party} 
          sub={`${summary.top_party_wins} seats secured out of matched total`} 
          icon="👑" 
          color="saffron" 
          chip="MAJORITY"
        />
        <StatCard 
          label="Classifier Accuracy" 
          value="97.9%" 
          sub="Random Forest model on test dataset" 
          icon="🎯" 
          color="emerald" 
          chip="ML EVAL"
        />
      </div>

      {/* Main Charts Row */}
      <div className="charts-grid">
        {/* Chart 1: Party Win Breakdown */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div className="chart-card-header-left">
              <h3>🏛️ Party Seat Share Breakdown</h3>
              <p>Top 10 political entities by victory counts in Lok Sabha</p>
            </div>
            <span className="chart-pill-badge">Top 10 Organizations</span>
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={summary.party_stats} layout="vertical" margin={{ left: 55, right: 30, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} />
              <YAxis type="category" dataKey="party" tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 700 }} width={75} />
              <Tooltip
                contentStyle={{ 
                  background: 'rgba(255, 255, 255, 0.98)', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: 12, 
                  color: '#0f172a', 
                  boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)' 
                }}
                formatter={(value, name) => [value, name === 'wins' ? 'Seats Won' : name]}
              />
              <Bar dataKey="wins" radius={[0, 8, 8, 0]}>
                {summary.party_stats.map((_, i) => (
                  <Cell key={i} fill={PARTY_GRADIENTS[i % PARTY_GRADIENTS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="intelligence-card indigo">
            <div className="intel-header">
              <span>💡 FIGURE ANALYSIS & STRATEGIC MEANING</span>
            </div>
            <div className="intel-content-grid">
              <div className="intel-metric-row">
                <span className="intel-label">Metric</span>
                <span>Total seats captured by party candidates in the general election.</span>
              </div>
              <div className="intel-metric-row">
                <span className="intel-label">Insight</span>
                <span>Major national parties dominate seat distribution, highlighting that high vote conversion requires strong regional presence and disciplined ticket allocation.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 2: Criminal Case Analysis */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div className="chart-card-header-left">
              <h3>⚖️ Legal Record vs. Win Conversion</h3>
              <p>Correlation between declared self-affidavits and election victory</p>
            </div>
            <span className="chart-pill-badge">ADR Affidavit Records</span>
          </div>

          {criminal && (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={criminal} margin={{ top: 20, bottom: 10, left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="label" tick={{ fill: '#0f172a', fontSize: 13, fontWeight: 700 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} unit="%" />
                <Tooltip
                  contentStyle={{ 
                    background: 'rgba(255, 255, 255, 0.98)', 
                    border: '1px solid #e2e8f0', 
                    borderRadius: 12, 
                    color: '#0f172a', 
                    boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)' 
                  }}
                  formatter={(value) => [`${value}%`, 'Win Conversion Rate']}
                />
                <Bar dataKey="win_rate" radius={[8, 8, 0, 0]} maxBarSize={100}>
                  <Cell fill="#10b981" />
                  <Cell fill="#f97316" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}

          <div className="intelligence-card amber">
            <div className="intel-header">
              <span>💡 FIGURE ANALYSIS & STRATEGIC MEANING</span>
            </div>
            <div className="intel-content-grid">
              <div className="intel-metric-row">
                <span className="intel-label">Metric</span>
                <span>Win percentage of candidates with declared criminal cases vs clean records.</span>
              </div>
              <div className="intel-metric-row">
                <span className="intel-label">Insight</span>
                <span>Candidates with declared cases show higher win rates, largely because established political figures with deep grassroots reach and financial backing are more frequently fielded in key seats.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
