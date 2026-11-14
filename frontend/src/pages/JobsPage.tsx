import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import CriteriaEditor from "../components/CriteriaEditor";
import { ErrorBox } from "../components/ui";
import type { Criterion, Job } from "../types";

const STARTER_CRITERIA: Criterion[] = [
  { label: "", weight: 3, must_have: true },
  { label: "", weight: 2, must_have: false },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.listJobs().then(setJobs).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Vacancies</h1>
          <p className="muted">Create a vacancy, define what matters, then upload CVs.</p>
        </div>
        {!creating && <button className="btn btn-primary" onClick={() => setCreating(true)}>New vacancy</button>}
      </div>
      <ErrorBox error={error} />
      {creating && <JobForm onCancel={() => setCreating(false)} />}

      {jobs === null ? (
        <p className="muted">Loading…</p>
      ) : jobs.length === 0 && !creating ? (
        <div className="empty card">
          <h2>No vacancies yet</h2>
          <p className="muted">Create your first vacancy to start analysing CVs.</p>
          <button className="btn btn-primary" onClick={() => setCreating(true)}>New vacancy</button>
        </div>
      ) : (
        <div className="job-grid">
          {jobs.map((j) => (
            <Link to={`/jobs/${j.id}`} key={j.id} className="card job-card">
              <div className="job-card-head">
                <h2>{j.title}</h2>
                <span className={`pill pill-job-${j.status}`}>{j.status}</span>
              </div>
              <p className="muted">{[j.department, j.location].filter(Boolean).join(" · ") || "—"}</p>
              <div className="stats">
                <span><b>{j.application_count}</b> applicants</span>
                <span><b>{j.analysed_count}</b> assessed</span>
                {j.processing_count > 0 && <span className="processing"><b>{j.processing_count}</b> analysing</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

function JobForm({ onCancel }: { onCancel: () => void }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState<Criterion[]>(STARTER_CRITERIA);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const filled = criteria.filter((c) => c.label.trim());
    if (!filled.length) return setError("Add at least one criterion.");
    setSaving(true);
    setError(null);
    try {
      const job = await api.createJob({ title, department, location, description, criteria: filled });
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>New vacancy</h2>
      <div className="form-grid">
        <label>Job title<input required minLength={2} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>Department<input value={department} onChange={(e) => setDepartment(e.target.value)} /></label>
        <label>Location<input value={location} onChange={(e) => setLocation(e.target.value)} /></label>
      </div>
      <label>Job description
        <textarea required minLength={10} rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <fieldset>
        <legend>Assessment criteria</legend>
        <p className="muted small">
          Each candidate is scored 0–5 per criterion, with evidence from their CV. Weights decide how much each
          criterion counts. Must-have gaps are flagged for you to check; they never reject anyone automatically.
        </p>
        <CriteriaEditor value={criteria} onChange={setCriteria} />
      </fieldset>
      <ErrorBox error={error} />
      <div className="actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" disabled={saving}>{saving ? "Creating…" : "Create vacancy"}</button>
      </div>
    </form>
  );
}
