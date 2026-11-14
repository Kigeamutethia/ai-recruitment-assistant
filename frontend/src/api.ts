import type { ApplicationDetail, ApplicationSummary, Criterion, Decision, Job, UploadResult } from "./types";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      const d = body.detail;
      message = typeof d === "string" ? d : d?.message ?? (Array.isArray(d) ? d.map((e: any) => e.msg).join("; ") : message);
    } catch { /* non-JSON error body */ }
    throw new ApiError(message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export interface JobInput {
  title: string;
  department?: string;
  location?: string;
  description: string;
  criteria: Criterion[];
}

export const api = {
  health: () => request<{ status: string; ai_provider: string }>("/health"),
  listJobs: () => request<Job[]>("/jobs"),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  createJob: (body: JobInput) => request<Job>("/jobs", json("POST", body)),
  updateJob: (id: string, body: Partial<JobInput> & { status?: Job["status"] }) =>
    request<Job>(`/jobs/${id}`, json("PATCH", body)),
  deleteJob: (id: string) => request<void>(`/jobs/${id}`, { method: "DELETE" }),
  listApplications: (jobId: string) => request<ApplicationSummary[]>(`/jobs/${jobId}/applications`),
  uploadCvs: (jobId: string, files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<UploadResult>(`/jobs/${jobId}/applications`, { method: "POST", body: form });
  },
  getApplication: (id: string) => request<ApplicationDetail>(`/applications/${id}`),
  reanalyse: (id: string) => request<{ status: string }>(`/applications/${id}/reanalyse`, { method: "POST" }),
  review: (id: string, body: { reviewer: string; decision: Decision; notes?: string }) =>
    request(`/applications/${id}/reviews`, json("POST", body)),
  deleteApplication: (id: string) => request<void>(`/applications/${id}`, { method: "DELETE" }),
  cvUrl: (id: string) => `/api/applications/${id}/cv`,
};
