import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { fetchFeatureImportance, fetchPartyWinrates, fetchEducationAnalysis } from '../api';

const VIBRANT_PALETTE = [
  '#4f46e5', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b',
  '#f43f5e', '#8b5cf6', '#0ea5e9', '#059669', '#ea580c'
];

export default function Insights() {
  const [features, setFeatures] = useState([]);
  const [partyWinrates, setPartyWinrates] = useState([]);
  const [education, setEducation] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchFeatureImportance(), fetchPartyWinrates(), fetchEducationAnalysis()])
      .then(([f, p, e]) => {
        setFeatures(f.features || []);
        setPartyWinrates(p.party_winrates || []);
        setEducation(e.education_analysis || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading-box">
        <div className="lux-spinner"></div>
        <p>Computing demographic & model insights...</p>
      </div>
    );
  }

  return (
    <div>
      {/* Hero Header */}
      <div className="page-hero">
        <div className="page-hero-title-group">
          <h2>Analytical Intelligence & ML Insights</h2>
          <p>Explainable AI feature weights, party conversion strike rates, and educational attainment correlations</p>
        </div>
        <div className="page-pill-tag">
          <span>🧠</span>
          <span>Scikit-Learn Random Forest Pipeline</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Chart 1: ML Feature Importance */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div className="chart-card-header-left">
              <h3>🧠 Feature Importance Weights</h3>
              <p>Top algorithmic drivers determining election victory or loss</p>
            </div>
            <span className="chart-pill-badge">Gini Relative Score</span>
          </div>

          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={features} layout="vertical" margin={{ left: 110, right: 30, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis type="category" dataKey="feature" tick={{ fill: '#0f172a', fontSize: 11, fontWeight: 700 }} width={130} />
              <Tooltip
                contentStyle={{ 
                  background: 'rgba(255, 255, 255, 0.98)', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: 12, 
                  color: '#0f172a', 
                  boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)' 
                }}
                formatter={(value) => [`${(value * 100).toFixed(2)}%`, 'Relative Weight']}
              />
              <Bar dataKey="importance" radius={[0, 8, 8, 0]}>
                {features.map((_, i) => (
                  <Cell key={i} fill={VIBRANT_PALETTE[i % VIBRANT_PALETTE.length]} />
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
                <span>Relative decision tree Gini importance assigned across all 15 input variables.</span>
              </div>
              <div className="intel-metric-row">
                <span className="intel-label">Insight</span>
                <span>National party affiliation (e.g. <code>party_BJP</code>) and non-affiliation (<code>party_IND</code>) account for over 37% of model decisions, proving party symbol power far outweighs individual qualifications.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 2: Win Rate by Party */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div className="chart-card-header-left">
              <h3>🏛️ Party Conversion Strike Rate</h3>
              <p>Percentage of fielded candidates securing victory (Min 10 candidates)</p>
            </div>
            <span className="chart-pill-badge">Electoral Efficiency</span>
          </div>

          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={partyWinrates.slice(0, 10)} layout="vertical" margin={{ left: 65, right: 30, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" unit="%" tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis type="category" dataKey="party" tick={{ fill: '#0f172a', fontSize: 11, fontWeight: 700 }} width={80} />
              <Tooltip
                contentStyle={{ 
                  background: 'rgba(255, 255, 255, 0.98)', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: 12, 
                  color: '#0f172a', 
                  boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)' 
                }}
                formatter={(value, name) => [name === 'win_rate' ? `${value}%` : value, name === 'win_rate' ? 'Strike Rate' : 'Candidates']}
              />
              <Bar dataKey="win_rate" radius={[0, 8, 8, 0]}>
                {partyWinrates.slice(0, 10).map((_, i) => (
                  <Cell key={i} fill={VIBRANT_PALETTE[i % VIBRANT_PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="intelligence-card emerald">
            <div className="intel-header">
              <span>💡 FIGURE ANALYSIS & STRATEGIC MEANING</span>
            </div>
            <div className="intel-content-grid">
              <div className="intel-metric-row">
                <span className="intel-label">Metric</span>
                <span>Proportion of fielded candidates who won their respective constituencies.</span>
              </div>
              <div className="intel-metric-row">
                <span className="intel-label">Insight</span>
                <span>High strike rates reflect targeted alliance formations and concentrated voter bases, rather than simply contesting an excessive number of unviable seats.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 3: Educational Attainment Analysis */}
        <div className="chart-card" style={{ gridColumn: '1 / -1' }}>
          <div className="chart-card-header">
            <div className="chart-card-header-left">
              <h3>🎓 Educational Attainment vs. Candidate Strike Rate</h3>
              <p>Success probability across self-declared highest educational qualifications</p>
            </div>
            <span className="chart-pill-badge">Self-Affidavit Filings</span>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={education} margin={{ top: 15, bottom: 15, left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="education" tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 700 }} angle={-10} textAnchor="end" height={40} />
              <YAxis unit="%" tick={{ fill: '#64748b', fontSize: 12 }} />
              <Tooltip
                contentStyle={{ 
                  background: 'rgba(255, 255, 255, 0.98)', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: 12, 
                  color: '#0f172a', 
                  boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)' 
                }}
                formatter={(value, name) => [name === 'win_rate' ? `${value}%` : value, name === 'win_rate' ? 'Win Rate' : 'Candidate Count']}
              />
              <Bar dataKey="win_rate" radius={[8, 8, 0, 0]} maxBarSize={60}>
                {education.map((_, i) => (
                  <Cell key={i} fill={VIBRANT_PALETTE[i % VIBRANT_PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="intelligence-card cyan">
            <div className="intel-header">
              <span>💡 FIGURE ANALYSIS & STRATEGIC MEANING</span>
            </div>
            <div className="intel-content-grid">
              <div className="intel-metric-row">
                <span className="intel-label">Metric</span>
                <span>Win percentage distribution grouped by candidate degree categories.</span>
              </div>
              <div className="intel-metric-row">
                <span className="intel-label">Insight</span>
                <span>Doctorates and Post Graduates demonstrate measurable success rates, but educational degrees are not significant differentiators relative to party apparatus strength.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
