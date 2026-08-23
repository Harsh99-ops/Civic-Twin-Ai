import { useEffect, useState, useCallback, useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Gauge, IndianRupee, TrendingUp, ListOrdered, Loader2 } from "lucide-react";
import { getStats, getPrioritize } from "../api";
import { formatINR, formatPercent, SEVERITY_COLOR, ROAD_COLOR } from "../constants";
import "./Dashboard.css";

const DEFAULT_BUDGET = 500000;

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [budget, setBudget] = useState(DEFAULT_BUDGET);
  const [prioritize, setPrioritize] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(() => {
    getStats().then(setStats).catch(() => setStats(null));
  }, []);

  const loadPrioritize = useCallback((b) => {
    setLoading(true);
    getPrioritize(b, 50)
      .then(setPrioritize)
      .catch(() => setPrioritize(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    const t = setTimeout(() => loadPrioritize(budget), 300);
    return () => clearTimeout(t);
  }, [budget, loadPrioritize]);

  const pieData = useMemo(() => {
    if (!prioritize?.road_cost_breakdown) return [];
    return Object.entries(prioritize.road_cost_breakdown).map(([name, value]) => ({ name, value }));
  }, [prioritize]);

  const allZones = useMemo(() => {
    if (!prioritize) return [];
    const funded = (prioritize.funded_zones || []).map((z) => ({ ...z, funded: true }));
    const unfunded = (prioritize.unfunded_zones || []).map((z) => ({ ...z, funded: false }));
    return [...funded, ...unfunded].sort((a, b) => a.priority_rank - b.priority_rank);
  }, [prioritize]);

  return (
    <div className="dash-page">
      <div className="dash-page__header">
        <h1>Priority Engine</h1>
        <p>Risk-scored zones, budget-aware repair prioritization, and cost breakdown by road authority</p>
      </div>

      <div className="stat-cards">
        <StatCard icon={<Gauge size={16} />} label="Total Complaints" value={stats?.total_complaints ?? "…"} />
        <StatCard
          icon={<TrendingUp size={16} />}
          label="Critical / High Risk"
          value={stats?.critical_or_high ?? "…"}
          accent="var(--sev-high)"
        />
        <StatCard
          icon={<ListOrdered size={16} />}
          label="Zones Funded"
          value={prioritize ? `${prioritize.summary.zones_funded} / ${prioritize.summary.zones_funded + prioritize.summary.zones_unfunded}` : "…"}
          accent="var(--brand)"
        />
        <StatCard
          icon={<IndianRupee size={16} />}
          label="Risk Addressed"
          value={prioritize ? formatPercent(prioritize.summary.risk_addressed_percent) : "…"}
          accent="var(--road-nhai)"
        />
      </div>

      <div className="dash-grid">
        {/* Budget + pie chart */}
        <div className="panel">
          <div className="panel__head">
            <IndianRupee size={16} />
            <span>Maintenance Budget</span>
          </div>
          <p className="panel__subtitle">Adjust the repair budget to see how the priority engine allocates it</p>

          <div className="budget-value">{formatINR(budget)}</div>
          <input
            type="range"
            min="50000"
            max="3000000"
            step="25000"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            className="budget-slider"
          />
          <div className="budget-slider__range">
            <span>₹50K</span>
            <span>₹30L</span>
          </div>

          {prioritize && (
            <div className="budget-summary">
              <div className="budget-summary__row">
                <span>Spent</span>
                <b>{formatINR(prioritize.summary.total_spent)}</b>
              </div>
              <div className="budget-summary__row">
                <span>Remaining</span>
                <b>{formatINR(prioritize.summary.remaining_budget)}</b>
              </div>
            </div>
          )}

          <div className="panel__head" style={{ marginTop: 26 }}>
            <span>Repair Cost by Road Authority</span>
          </div>
          <p className="panel__subtitle">Total estimated repair cost across all scored zones</p>

          {pieData.length > 0 ? (
            <div className="pie-wrap">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={ROAD_COLOR[entry.name] || "#8b96a8"} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v) => formatINR(v)}
                    contentStyle={{ background: "#131a26", border: "1px solid #1e2733", borderRadius: 8, fontSize: 12 }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={30}
                    formatter={(v) => <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>{v}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-note">No cost data yet.</div>
          )}
        </div>

        {/* Priority table */}
        <div className="panel">
          <div className="panel__head">
            <ListOrdered size={16} />
            <span>Zone Priority List</span>
            {loading && <Loader2 size={14} className="spin" style={{ marginLeft: "auto" }} />}
          </div>
          <p className="panel__subtitle">Ranked by risk-reduction-per-rupee, funded first within the current budget</p>

          <div className="priority-table-wrap">
            <table className="priority-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Zone</th>
                  <th>Category</th>
                  <th>Severity</th>
                  <th>Road</th>
                  <th>Cost</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {allZones.map((z) => (
                  <tr key={z.zone_id}>
                    <td className="mono">{z.priority_rank}</td>
                    <td className="mono">
                      {z.latitude}, {z.longitude}
                    </td>
                    <td>{z.dominant_category}</td>
                    <td>
                      <span className="severity-dot" style={{ background: SEVERITY_COLOR[z.risk_level] }} />
                      {z.risk_level} ({z.risk_score})
                    </td>
                    <td>
                      <span className={`road-pill ${z.road_type === "NHAI" ? "road-pill--nhai" : ""}`}>
                        {z.road_type}
                      </span>
                    </td>
                    <td className="mono">{formatINR(z.estimated_cost)}</td>
                    <td>
                      <span className={`funded-pill ${z.funded ? "funded-pill--yes" : ""}`}>
                        {z.funded ? "Funded" : "Pending"}
                      </span>
                    </td>
                  </tr>
                ))}
                {allZones.length === 0 && (
                  <tr>
                    <td colSpan={7} className="empty-note">
                      {loading ? "Loading…" : "No zones scored yet."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, accent = "var(--brand)" }) {
  return (
    <div className="stat-card">
      <div className="stat-card__icon" style={{ color: accent, background: `${accent}22` }}>
        {icon}
      </div>
      <div>
        <div className="stat-card__value">{value}</div>
        <div className="stat-card__label">{label}</div>
      </div>
    </div>
  );
}
