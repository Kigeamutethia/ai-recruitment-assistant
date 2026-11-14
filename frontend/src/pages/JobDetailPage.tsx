import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import CriteriaEditor from "../components/CriteriaEditor";
import UploadZone from "../components/UploadZone";
import { ErrorBox, ScoreBar, StatusPill } from "../components/ui";
import type { ApplicationSummary, Criterion, Job } from "../types";

const POLL_MS = 3000;

export default function JobDetailPage() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [apps, setApps] = useState<ApplicationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [weights, setWeights] = useState<Criterion[] | null>(null);
  const [filter, setFilter] = useState<"all" | "review" | "decided">("all");

  const load = useCallback(async () => {
    try {
      const [j, a] = await Promise.all([api.getJob(jobId), api.listApplications(jobId)]);
      setJob(j);
      setApps(a);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [jobId]);

  useEffect(() => { load(); }, [load]);

  // Poll while any CV is still being analysed.
  const busy = apps.some((a) => a.status === "received" || a.status === "processing");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [busy, load]);

  if (!job) return error ? <ErrorBox error={error} /> : <p className="muted">Loading…</p>;

  async function saveWeights() {
    if (!weights) return;
    try {
      await api.updateJob(jobId, { criteria: weights });
      setWeights(null);
      await load(); // scores are recomputed server-side with the new weights
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function toggleStatus() {
    const next = job!.status === "open" ? "closed" : "open";
    setJob(await api.updateJob(jobId, { status: next }));
  }

  async function remove() {
    if (!confirm(`Delete "${job!.title}" and all ${job!.application_count} applications? This cannot be undone.`)) return;
    await api.deleteJob(jobId);
    navigate("/");
  }

  const decided = (a: ApplicationSummary) => ["shortlisted", "on_hold", "not_progressing"].includes(a.status);
  const visible = apps.filter((a) =>
    filter === "all" ? true : filter === "review" ? a.status === "analysed" : decided(a));

  return (
    <>
      <nav className="crumbs"><Link to="/">Vacancies</Link> / {job.title}</nav>
      <div className="page-head">
        <div>
          <h1>{job.title} <span className={`pill pill-job-${job.status}`}>{job.status}</span></h1>
          <p className="muted">{[job.department, job.location].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="actions">
          <button className="btn btn-ghost" onClick={toggleStatus}>{job.status === "open" ? "Close vacancy" : "Reopen"}</button>
          <button className="btn btn-danger-ghost" onClick={remove}>Delete</button>
        </div>
      </div>
      <ErrorBox error={error} />

      <div className="layout-2col">
        <section className="card">
          <div className="section-head">
            <h2>Candidates <span className="muted">({apps.length})</span></h2>
            <div className="segmented" role="tablist">
              {(["all", "review", "decided"] as const).map((f) => (
                <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? "active" : ""}
                  onClick={() => setFilter(f)}>
                  {f === "all" ? "All" : f === "review" ? "Awaiting review" : "Decided"}
                </button>
              ))}
            </div>
          </div>
          {busy && <p className="processing small">Analysing CVs… this list refreshes automatically.</p>}
          {visible.length === 0 ? (
            <p className="muted empty">{apps.length ? "No candidates match this filter." : "No CVs yet. Upload some to get started."}</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>#</th><th>Candidate</th><th>Score</th><th>Experience</th><th>Key skills</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {visible.map((a, i) => (
                    <tr key={a.id} onClick={() => navigate(`/applications/${a.id}`)} className="clickable">
                      <td className="muted">{a.overall_score !== null ? i + 1 : ""}</td>
                      <td>
                        <Link to={`/applications/${a.id}`} onClick={(e) => e.stopPropagation()}>
                          {a.candidate_name || a.cv_filename}
                        </Link>
                        {a.must_have_met === false && <span className="flag" title="One or more must-have criteria lack evidence">must-have gap</span>}
                        {a.failure_reason && <div className="small error-text">{a.failure_reason}</div>}
                      </td>
                      <td><ScoreBar score={a.overall_score} /></td>
                      <td>{a.total_years_experience != null ? `${a.total_years_experience} yrs` : "—"}</td>
                      <td className="skills-cell">{a.top_skills.slice(0, 4).map((s) => <span key={s} className="chip">{s}</span>)}</td>
                      <td><StatusPill status={a.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="stack">
          <section className="card">
            <h2>Upload CVs</h2>
            <UploadZone jobId={jobId} onUploaded={load} />
          </section>
          <section className="card">
            <div className="section-head">
              <h2>Criteria & weights</h2>
              {weights && <button className="btn btn-primary btn-sm" onClick={saveWeights}>Save & re-rank</button>}
            </div>
            <p className="muted small">Changing weights re-ranks candidates instantly. No new AI calls are needed.</p>
            <CriteriaEditor value={weights ?? job.criteria} onChange={setWeights} weightsOnly />
            {weights && <button className="btn btn-ghost btn-sm" onClick={() => setWeights(null)}>Discard changes</button>}
          </section>
          <details className="card">
            <summary><h2 className="inline">Job description</h2></summary>
            <p className="prewrap">{job.description}</p>
          </details>
        </aside>
      </div>
    </>
  );
}
