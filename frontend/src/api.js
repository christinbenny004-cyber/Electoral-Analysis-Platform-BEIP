const API_BASE = "http://localhost:8000/api";

export async function fetchSummary() {
  const res = await fetch(`${API_BASE}/elections/summary`);
  return res.json();
}

export async function fetchResults({ page = 1, state, party, year, search }) {
  const params = new URLSearchParams({ page, per_page: 50 });
  if (state) params.append("state", state);
  if (party) params.append("party", party);
  if (year) params.append("year", year);
  if (search) params.append("search", search);
  const res = await fetch(`${API_BASE}/elections/results?${params}`);
  return res.json();
}

export async function fetchStates() {
  const res = await fetch(`${API_BASE}/elections/states`);
  return res.json();
}

export async function fetchParties() {
  const res = await fetch(`${API_BASE}/elections/parties`);
  return res.json();
}

export async function predictOutcome(profile) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  return res.json();
}

export async function fetchFeatureImportance() {
  const res = await fetch(`${API_BASE}/insights/feature-importance`);
  return res.json();
}

export async function fetchPartyWinrates() {
  const res = await fetch(`${API_BASE}/insights/party-winrates`);
  return res.json();
}

export async function fetchCriminalAnalysis() {
  const res = await fetch(`${API_BASE}/insights/criminal-analysis`);
  return res.json();
}

export async function fetchEducationAnalysis() {
  const res = await fetch(`${API_BASE}/insights/education-analysis`);
  return res.json();
}
