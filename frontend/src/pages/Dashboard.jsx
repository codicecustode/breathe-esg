import { useEffect, useState, useCallback } from "react";
import { getEmissions, getEmissionsSummary } from "../api";
import styles from "./Dashboard.module.css";

const SCOPES = ["", "Scope 1", "Scope 2", "Scope 3"];
const STATUSES = ["", "PENDING", "APPROVED", "REJECTED"];
const SOURCES = ["", "SAP", "UTILITY", "TRAVEL"];

export default function Dashboard() {
  const [records, setRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ scope: "", review_status: "", source_type: "" });

  const load = useCallback(() => {
    setLoading(true);
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    Promise.all([getEmissions(params), getEmissionsSummary(params)])
      .then(([r, s]) => {
        setRecords(r.data);
        setSummary(s.data);
        setError(null);
      })
      .catch(() => setError("Backend unavailable — is Django running on port 8000?"))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const setFilter = (key, val) => setFilters((f) => ({ ...f, [key]: val }));

  return (
    <div>
      <h1 className={styles.title}>Emissions Dashboard</h1>

      {summary && (
        <div className={styles.cards}>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Total CO₂e (kg)</div>
            <div className={styles.cardValue}>{summary.total_emissions.toLocaleString("en-IN", { maximumFractionDigits: 1 })}</div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Scope 1 (kg)</div>
            <div className={`${styles.cardValue} ${styles.scope1}`}>{summary.by_scope["Scope 1"].toLocaleString("en-IN", { maximumFractionDigits: 1 })}</div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Scope 2 (kg)</div>
            <div className={`${styles.cardValue} ${styles.scope2}`}>{summary.by_scope["Scope 2"].toLocaleString("en-IN", { maximumFractionDigits: 1 })}</div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Scope 3 (kg)</div>
            <div className={`${styles.cardValue} ${styles.scope3}`}>{summary.by_scope["Scope 3"].toLocaleString("en-IN", { maximumFractionDigits: 1 })}</div>
          </div>
          <div className={`${styles.card} ${summary.suspicious_count > 0 ? styles.warn : ""}`}>
            <div className={styles.cardLabel}>Suspicious</div>
            <div className={styles.cardValue}>{summary.suspicious_count}</div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Pending Review</div>
            <div className={styles.cardValue}>{summary.by_status.PENDING}</div>
          </div>
        </div>
      )}

      {summary && (
        <div className={styles.sourcebar}>
          {Object.entries(summary.by_source).map(([src, val]) => (
            <div key={src} className={styles.sourcechip}>
              <span className={`${styles.dot} ${styles[src.toLowerCase()]}`} />
              <strong>{src}</strong> {val.toLocaleString("en-IN", { maximumFractionDigits: 1 })} kg CO₂e
            </div>
          ))}
        </div>
      )}

      <div className={styles.filters}>
        <select value={filters.scope} onChange={(e) => setFilter("scope", e.target.value)}>
          {SCOPES.map((s) => <option key={s} value={s}>{s || "All Scopes"}</option>)}
        </select>
        <select value={filters.review_status} onChange={(e) => setFilter("review_status", e.target.value)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s || "All Statuses"}</option>)}
        </select>
        <select value={filters.source_type} onChange={(e) => setFilter("source_type", e.target.value)}>
          {SOURCES.map((s) => <option key={s} value={s}>{s || "All Sources"}</option>)}
        </select>
        <button className={styles.refreshBtn} onClick={load}>Refresh</button>
      </div>

      {loading && <p className={styles.loading}>Loading...</p>}
      {error && <p className={styles.error}>{error}</p>}

      {!loading && !error && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Source</th>
              <th>Activity</th>
              <th>Scope</th>
              <th>Quantity</th>
              <th>Factor</th>
              <th>CO₂e (kg)</th>
              <th>Date / Period</th>
              <th>Status</th>
              <th>Flag</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 && (
              <tr>
                <td colSpan={9} className={styles.empty}>
                  No records. Upload a file on the Upload page to get started.
                </td>
              </tr>
            )}
            {records.map((r) => (
              <tr key={r.id} className={r.suspicious ? styles.suspicious : ""}>
                <td><span className={`${styles.srcbadge} ${styles[r.source_type?.toLowerCase()]}`}>{r.source_type}</span></td>
                <td className={styles.activity}>{r.activity_type}</td>
                <td>{r.scope}</td>
                <td>{r.quantity?.toLocaleString("en-IN", { maximumFractionDigits: 2 })} {r.normalized_unit}</td>
                <td className={styles.factor}>{r.emission_factor}</td>
                <td className={styles.emissions}>{r.calculated_emissions?.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                <td className={styles.date}>
                  {r.period_start
                    ? `${r.period_start} → ${r.period_end}`
                    : r.date || "—"}
                </td>
                <td>
                  <span className={`${styles.badge} ${styles[r.review_status?.toLowerCase()]}`}>
                    {r.review_status}
                  </span>
                </td>
                <td className={styles.flag}>
                  {r.suspicious ? <span title={r.suspicious_reason}>⚠</span> : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
