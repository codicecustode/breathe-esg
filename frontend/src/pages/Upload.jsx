import { useState, useEffect } from "react";
import {
  getTenants, createTenant,
  getDataSources, createDataSource,
  getImportJobs, uploadImportJob,
} from "../api";
import styles from "./Upload.module.css";

export default function Upload() {
  const [tenants, setTenants] = useState([]);
  const [sources, setSources] = useState([]);
  const [jobs, setJobs] = useState([]);

  const [tenantId, setTenantId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  const [newTenantName, setNewTenantName] = useState("");
  const [newSourceName, setNewSourceName] = useState("");
  const [newSourceType, setNewSourceType] = useState("SAP");
  const [newSourceTenant, setNewSourceTenant] = useState("");

  const reload = () => {
    getTenants().then((r) => setTenants(r.data)).catch(() => {});
    getDataSources().then((r) => setSources(r.data)).catch(() => {});
    getImportJobs().then((r) => setJobs(r.data)).catch(() => {});
  };

  useEffect(() => { reload(); }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !tenantId || !sourceId) {
      setMessage({ type: "error", text: "Tenant, Data Source, and file are all required." });
      return;
    }
    const fd = new FormData();
    fd.append("tenant", tenantId);
    fd.append("source", sourceId);
    fd.append("uploaded_file", file);
    setSubmitting(true);
    setMessage(null);
    try {
      const res = await uploadImportJob(fd);
      const job = res.data;
      setMessage({
        type: job.status === "COMPLETED" ? "success" : "warn",
        text: job.status === "COMPLETED"
          ? `Processed ${job.row_count} emission records.`
          : `Import ${job.status}. ${job.error_log || "Check backend logs."}`,
      });
      reload();
    } catch (err) {
      setMessage({ type: "error", text: "Upload failed. " + (err.response?.data?.detail || "") });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateTenant = async (e) => {
    e.preventDefault();
    if (!newTenantName.trim()) return;
    await createTenant({ name: newTenantName });
    setNewTenantName("");
    reload();
  };

  const handleCreateSource = async (e) => {
    e.preventDefault();
    if (!newSourceName.trim() || !newSourceTenant) return;
    await createDataSource({ name: newSourceName, source_type: newSourceType, tenant: newSourceTenant });
    setNewSourceName("");
    reload();
  };

  const filteredSources = tenantId ? sources.filter((s) => String(s.tenant) === tenantId) : sources;

  return (
    <div>
      <h1 className={styles.title}>Upload Emissions Data</h1>

      <div className={styles.grid}>
        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Upload File</h2>
          <form className={styles.form} onSubmit={handleUpload}>
            <label>
              Tenant
              <select value={tenantId} onChange={(e) => { setTenantId(e.target.value); setSourceId(""); }}>
                <option value="">Select tenant…</option>
                {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label>
              Data Source
              <select value={sourceId} onChange={(e) => setSourceId(e.target.value)} disabled={!tenantId}>
                <option value="">Select data source…</option>
                {filteredSources.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} ({s.source_type})</option>
                ))}
              </select>
            </label>
            <label>
              File
              <input type="file" accept=".csv,.json" onChange={(e) => setFile(e.target.files[0])} />
              <span className={styles.hint}>CSV for SAP/Utility · JSON for Travel</span>
            </label>
            {message && (
              <p className={styles[message.type]}>{message.text}</p>
            )}
            <button type="submit" disabled={submitting}>
              {submitting ? "Processing…" : "Upload & Process"}
            </button>
          </form>
        </section>

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Setup</h2>

          <h3 className={styles.subhead}>Create Tenant</h3>
          <form className={styles.inlineForm} onSubmit={handleCreateTenant}>
            <input
              placeholder="Tenant name (e.g. Acme Corp)"
              value={newTenantName}
              onChange={(e) => setNewTenantName(e.target.value)}
            />
            <button type="submit">Add</button>
          </form>

          <h3 className={styles.subhead} style={{ marginTop: "1.25rem" }}>Create Data Source</h3>
          <form className={styles.form} onSubmit={handleCreateSource}>
            <label>
              Tenant
              <select value={newSourceTenant} onChange={(e) => setNewSourceTenant(e.target.value)}>
                <option value="">Select tenant…</option>
                {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label>
              Name
              <input
                placeholder="e.g. SAP Plant 1000 — Fuel"
                value={newSourceName}
                onChange={(e) => setNewSourceName(e.target.value)}
              />
            </label>
            <label>
              Type
              <select value={newSourceType} onChange={(e) => setNewSourceType(e.target.value)}>
                <option value="SAP">SAP</option>
                <option value="UTILITY">Utility</option>
                <option value="TRAVEL">Travel</option>
              </select>
            </label>
            <button type="submit">Add Source</button>
          </form>
        </section>
      </div>

      <h2 className={styles.sectionTitle} style={{ marginTop: "2rem" }}>Recent Import Jobs</h2>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Source</th>
            <th>Status</th>
            <th>Rows</th>
            <th>Uploaded</th>
            <th>Errors</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 && (
            <tr><td colSpan={6} style={{ textAlign: "center", padding: "1.5rem", color: "#6c757d" }}>No import jobs yet.</td></tr>
          )}
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td>
              <td>{j.source}</td>
              <td><span className={`${styles.badge} ${styles[j.status?.toLowerCase()]}`}>{j.status}</span></td>
              <td>{j.row_count}</td>
              <td>{j.created_at ? new Date(j.created_at).toLocaleString("en-IN") : "—"}</td>
              <td className={styles.errorLog}>{j.error_log || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
