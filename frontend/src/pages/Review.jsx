import { useEffect, useState } from "react";
import { getEmissions, approveRecord, rejectRecord, getAuditEvents } from "../api";
import styles from "./Review.module.css";

function AuditDrawer({ recordId, onClose }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAuditEvents(recordId)
      .then((r) => setEvents(r.data))
      .finally(() => setLoading(false));
  }, [recordId]);

  return (
    <div className={styles.drawer}>
      <div className={styles.drawerHeader}>
        <span>Audit Trail — Record #{recordId}</span>
        <button onClick={onClose}>✕</button>
      </div>
      {loading && <p className={styles.drawerBody}>Loading…</p>}
      {!loading && events.length === 0 && (
        <p className={styles.drawerBody}>No audit events yet.</p>
      )}
      {events.map((e) => (
        <div key={e.id} className={styles.auditEvent}>
          <span className={`${styles.auditAction} ${styles[e.action.toLowerCase()]}`}>{e.action}</span>
          <span className={styles.auditMeta}>
            {e.actor_username || "system"} · {new Date(e.timestamp).toLocaleString("en-IN")}
          </span>
          {e.note && <p className={styles.auditNote}>{e.note}</p>}
        </div>
      ))}
    </div>
  );
}

export default function Review() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);
  const [note, setNote] = useState("");
  const [activeDrawer, setActiveDrawer] = useState(null);
  const [filter, setFilter] = useState("PENDING");

  const load = () => {
    setLoading(true);
    const params = filter ? { review_status: filter } : {};
    getEmissions(params)
      .then((r) => { setRecords(r.data); setError(null); })
      .catch(() => setError("Backend unavailable — is Django running on port 8000?"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]);

  const act = async (id, action) => {
    setBusy(id);
    try {
      await (action === "approve" ? approveRecord(id, note) : rejectRecord(id, note));
      setNote("");
      load();
    } catch {
      alert("Action failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className={styles.shell}>
      <div className={styles.main}>
        <h1 className={styles.title}>Review Queue</h1>

        <div className={styles.toolbar}>
          <div className={styles.tabs}>
            {["PENDING", "APPROVED", "REJECTED", ""].map((s) => (
              <button
                key={s}
                className={`${styles.tab} ${filter === s ? styles.activeTab : ""}`}
                onClick={() => setFilter(s)}
              >
                {s || "All"}
              </button>
            ))}
          </div>
          <input
            className={styles.noteInput}
            placeholder="Optional note for next action…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>

        {loading && <p className={styles.loading}>Loading…</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && !error && (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Source</th>
                <th>Activity</th>
                <th>Scope</th>
                <th>CO₂e (kg)</th>
                <th>Date / Period</th>
                <th>Flag</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 && (
                <tr><td colSpan={8} className={styles.empty}>No records matching this filter.</td></tr>
              )}
              {records.map((r) => (
                <tr key={r.id} className={r.suspicious ? styles.suspicious : ""}>
                  <td>
                    <span className={`${styles.srcbadge} ${styles[r.source_type?.toLowerCase()]}`}>
                      {r.source_type}
                    </span>
                  </td>
                  <td className={styles.activity}>{r.activity_type}</td>
                  <td>{r.scope}</td>
                  <td className={styles.emval}>{r.calculated_emissions?.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                  <td className={styles.dateCol}>
                    {r.period_start ? `${r.period_start} → ${r.period_end}` : r.date || "—"}
                  </td>
                  <td className={styles.flag}>
                    {r.suspicious
                      ? <span className={styles.flagBadge} title={r.suspicious_reason}>⚠ {r.suspicious_reason}</span>
                      : "—"}
                  </td>
                  <td>
                    <span className={`${styles.badge} ${styles[r.review_status?.toLowerCase()]}`}>
                      {r.review_status}
                    </span>
                    {r.is_edited && <span className={styles.edited}>edited</span>}
                  </td>
                  <td className={styles.actions}>
                    {r.review_status === "PENDING" && (
                      <>
                        <button
                          className={styles.approve}
                          disabled={busy === r.id}
                          onClick={() => act(r.id, "approve")}
                        >Approve</button>
                        <button
                          className={styles.reject}
                          disabled={busy === r.id}
                          onClick={() => act(r.id, "reject")}
                        >Reject</button>
                      </>
                    )}
                    <button
                      className={styles.auditBtn}
                      onClick={() => setActiveDrawer(activeDrawer === r.id ? null : r.id)}
                    >
                      {activeDrawer === r.id ? "Hide" : "Audit"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {activeDrawer && (
        <AuditDrawer recordId={activeDrawer} onClose={() => setActiveDrawer(null)} />
      )}
    </div>
  );
}
