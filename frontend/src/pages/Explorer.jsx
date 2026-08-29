import { useState, useEffect } from 'react';
import { fetchResults, fetchStates, fetchParties } from '../api';

export default function Explorer() {
  const [data, setData] = useState(null);
  const [states, setStates] = useState([]);
  const [parties, setParties] = useState([]);
  const [filters, setFilters] = useState({ state: '', party: '', search: '', page: 1 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchStates(), fetchParties()])
      .then(([s, p]) => { setStates(s.states); setParties(p.parties); });
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchResults(filters)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [filters]);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  };

  const getPartyClass = (partyName) => {
    const p = (partyName || '').toUpperCase();
    if (p.includes('BJP')) return 'bjp';
    if (p.includes('INC') || p.includes('CONGRESS')) return 'inc';
    if (p.includes('AAP')) return 'aap';
    return 'ind';
  };

  const getInitials = (name) => {
    if (!name) return 'C';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div>
      {/* Hero Header */}
      <div className="page-hero">
        <div className="page-hero-title-group">
          <h2>Election Data Explorer</h2>
          <p>Search, inspect, and filter granular candidate records, party classifications, and legal profiles</p>
        </div>
        {data && (
          <div className="page-pill-tag">
            <span>📊</span>
            <span>{data.total.toLocaleString()} Records Indexed</span>
          </div>
        )}
      </div>

      {/* Table Container Card */}
      <div className="data-table-card">
        {/* Search & Filter Toolbar */}
        <div className="table-filter-bar">
          <div className="search-input-wrap">
            <span>🔍</span>
            <input
              type="text"
              placeholder="Search by candidate name or constituency..."
              value={filters.search}
              onChange={e => updateFilter('search', e.target.value)}
            />
          </div>

          <select 
            className="filter-select" 
            value={filters.state} 
            onChange={e => updateFilter('state', e.target.value)}
          >
            <option value="">🗺️ All States & UTs</option>
            {states.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          <select 
            className="filter-select" 
            value={filters.party} 
            onChange={e => updateFilter('party', e.target.value)}
          >
            <option value="">🏛️ All Political Parties</option>
            {parties.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        {/* Table Content */}
        {loading ? (
          <div className="loading-box">
            <div className="lux-spinner"></div>
            <p>Querying candidate database...</p>
          </div>
        ) : data && data.results.length > 0 ? (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Candidate Profile</th>
                  <th>Constituency</th>
                  <th>State</th>
                  <th>Party</th>
                  <th>Criminal Cases</th>
                  <th>Education</th>
                  <th>Electoral Result</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r, i) => (
                  <tr key={i}>
                    <td>
                      <div className="candidate-cell">
                        <div className="candidate-avatar">
                          {getInitials(r.candidate_name)}
                        </div>
                        <div>
                          <div>{r.candidate_name}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--text-title)' }}>
                      {r.constituency_name}
                    </td>
                    <td>{r.state_name}</td>
                    <td>
                      <span className={`party-tag ${getPartyClass(r.party)}`}>
                        {r.party}
                      </span>
                    </td>
                    <td>
                      <span style={{ 
                        fontWeight: 700, 
                        color: r.criminal_cases > 0 ? '#e11d48' : '#059669' 
                      }}>
                        {r.criminal_cases} {r.criminal_cases === 1 ? 'case' : 'cases'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
                      {r.education || 'Not Declared'}
                    </td>
                    <td>
                      <span className={`status-pill ${r.won === 1 ? 'win' : 'lose'}`}>
                        <span>{r.won === 1 ? '● WON' : '○ LOST'}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Controls */}
            <div className="table-pagination-bar">
              <span>
                Showing page <strong>{data.page}</strong> of <strong>{data.total_pages}</strong> ({data.total.toLocaleString()} total candidates)
              </span>
              <div className="pagination-btn-group">
                <button 
                  className="pagination-btn"
                  disabled={data.page <= 1} 
                  onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}
                >
                  ← Previous
                </button>
                <button 
                  className="pagination-btn"
                  disabled={data.page >= data.total_pages} 
                  onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="loading-box">
            <p>No candidate records found matching the active filter criteria.</p>
          </div>
        )}
      </div>
    </div>
  );
}
