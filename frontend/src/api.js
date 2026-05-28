import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : "/api",
});

export const getTenants = () => api.get("/tenants/");
export const createTenant = (data) => api.post("/tenants/", data);

export const getDataSources = (params) => api.get("/data-sources/", { params });
export const createDataSource = (data) => api.post("/data-sources/", data);

export const getEmissions = (params) => api.get("/emissions/", { params });
export const getEmissionsSummary = (params) => api.get("/emissions/summary/", { params });
export const approveRecord = (id, note) => api.post(`/emissions/${id}/approve/`, { note });
export const rejectRecord = (id, note) => api.post(`/emissions/${id}/reject/`, { note });

export const getImportJobs = () => api.get("/import-jobs/");
export const uploadImportJob = (formData) => api.post("/import-jobs/", formData);

export const getAuditEvents = (recordId) =>
  api.get("/audit-events/", { params: { record_id: recordId } });

export default api;
