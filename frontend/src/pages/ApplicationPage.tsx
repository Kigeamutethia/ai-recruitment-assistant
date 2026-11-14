import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Dots, ErrorBox, scoreBand, StatusPill } from "../components/ui";
import type { ApplicationDetail, Decision } from "../types";

const DECISIONS: { value: Decision; label: string }[] = [
  { value: "shortlisted", label: "Shortlist" },
  { value: "on_hold", label: "On hold" },
  { value: "not_progressing", label: "Not progressing" },
];
const REVIEWER_KEY = "reviewerName";

function readReviewer() {
  try { return localStorage.getItem(REVIEWER_KEY) ?? ""; } catch { return ""; }
}

export default function ApplicationPage() {
  const { appId = "" } = useParams();
  const navigate = useNavigate();
  const [app, setApp] = useState<ApplicationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () => api.getApplication(appId).then(setApp).catch((e) => setError(e.message)),
    [appId],
  );
  useEffect(() => { load(); }, [load]);

  const pending = app && (app.status === "received" || app.status === "processing");
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [pending, load]);

  if (!app) return error ? <ErrorBox error={error} /> : <p className="muted">Loading…</p>;
  const { candidate, profile, assessment: a } = app;

  async function reanalyse() {
    await api.reanalyse(appId).catch((e) => setError(e.message));
    load();
  }

  async function remove() {
    if (!confirm("Delete this application and its CV?")) return;
    await api.deleteApplication(appId);
    navigate(`/jobs/${app!.job.id}`);
  }

  return (
    <>
      <nav className="crumbs">
        <Link to="/">Vacancies</Link> / <Link to={`/jobs/${app.job.id}`}>{app.job.title}</Link> / {candidate.full_name}
      </nav>

      <div className="page-head">
        <div>
          <h1>{candidate.full_name || app.cv_filename} <StatusPill status={app.status} /></h1>
          <p className="muted">
            {[candidate.email, candidate.phone, candidate.location].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="actions">
          <a className="btn btn-ghost" href={api.cvUrl(app.id)} target="_blank" rel="noreferrer">View CV</a>
          <button className="btn btn-ghost" onClick={reanalyse} disabled={!!pending}>Re-analyse</button>
          <button className="btn btn-danger-ghost" onClick={remove}>Delete</button>
        </div>
      </div>
      <ErrorBox error={error} />

      {pending && <div className="alert alert-info">Analysis in progress…</div>}
      {app.status === "failed" && (
        <div className="alert alert-error">Analysis failed: {app.failure_reason}. You can re-analyse, or review the CV manually.</div>
      )}

      {a && (
        <div className="layout-2col">
          <div className="stack">
            <section className="card score-card">
              <div className={`score-big band-${scoreBand(a.overall_score)}`}>
                {Math.round(a.overall_score)}<small>/100</small>
              </div>
              <div>
                <p>
                  {a.must_have_met
                    ? "Evidence found for all must-have criteria."
                    : <span className="flag">One or more must-have criteria lack evidence. Please check before deciding.</span>}
                </p>
                <p className="muted small">
                  Advisory score from {a.model_name} (prompt {a.prompt_version}) based on CV evidence only.
                  {Math.abs(a.overall_score - a.score_at_analysis) > 0.01 &&
                    ` Re-weighted from ${a.score_at_analysis.toFixed(0)} at analysis time.`}
                </p>
              </div>
            </section>

            <section className="card">
              <h2>Assessment by criterion</h2>
              <ul className="criteria-results">
                {a.criteria.map((c) => (
                  <li key={c.key}>
                    <div className="criterion-head">
                      <span>
                        <b>{c.label}</b>
                        {c.must_have && <span className="tag">must-have</span>}
                        <span className="muted small"> · weight {c.weight}</span>
                      </span>
                      <Dots score={c.score} />
                    </div>
                    <p className="small">{c.reasoning}</p>
                    {c.evidence.length > 0 && (
                      <ul className="evidence">{c.evidence.map((q, i) => <li key={i}>“{q}”</li>)}</ul>
                    )}
                  </li>
                ))}
              </ul>
            </section>

            <div className="two-up">
              <section className="card">
                <h2>Strengths</h2>
                <ul className="bullets good">{a.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </section>
              <section className="card">
                <h2>Gaps to explore</h2>
                <ul className="bullets warn">{a.gaps.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </section>
            </div>

            <section className="card">
              <h2>Suggested interview questions</h2>
              <ol className="questions">
                {a.interview_questions.map((q, i) => (
                  <li key={i}>
                    <p>{q.question}</p>
                    <p className="muted small">{q.purpose}{q.criterion_key !== "general" && ` · ${q.criterion_key}`}</p>
                  </li>
                ))}
              </ol>
            </section>
          </div>

          <aside className="stack">
            <ReviewPanel app={app} onSaved={load} />
            {profile && (
              <section className="card">
                <h2>Extracted profile</h2>
                {profile.summary && <p>{profile.summary}</p>}
                {profile.total_years_experience != null && (
                  <p className="muted small">{profile.total_years_experience} years' professional experience</p>
                )}
                <h3>Skills</h3>
                <div className="chips">{profile.skills.map((s) => <span key={s.name} className="chip">{s.name}</span>)}</div>
                {profile.experience.length > 0 && (<>
                  <h3>Experience</h3>
                  <ul className="timeline">
                    {profile.experience.map((e, i) => (
                      <li key={i}>
                        <b>{e.title}</b>{e.company && ` · ${e.company}`}
                        {(e.start || e.end) && <div className="muted small">{e.start} – {e.end}</div>}
                      </li>
                    ))}
                  </ul>
                </>)}
                {profile.education.length > 0 && (<>
                  <h3>Education</h3>
                  <ul className="plain">
                    {profile.education.map((e, i) => (
                      <li key={i}>{e.qualification}{e.institution && `, ${e.institution}`}{e.year && ` (${e.year})`}</li>
                    ))}
                  </ul>
                </>)}
                {profile.certifications.length > 0 && (<>
                  <h3>Certifications</h3>
                  <ul className="plain">{profile.certifications.map((c) => <li key={c}>{c}</li>)}</ul>
                </>)}
              </section>
            )}
          </aside>
        </div>
      )}
    </>
  );
}

function ReviewPanel({ app, onSaved }: { app: ApplicationDetail; onSaved: () => void }) {
  const [reviewer, setReviewer] = useState(readReviewer);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const canReview = !["received", "processing"].includes(app.status);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!decision) return setError("Choose a decision.");
    try {
      try { localStorage.setItem(REVIEWER_KEY, reviewer); } catch { /* storage unavailable */ }
      await api.review(app.id, { reviewer, decision, notes: notes || undefined });
      setNotes("");
      setDecision(null);
      setError(null);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <section className="card">
      <h2>Your decision</h2>
      {canReview ? (
        <form className="form" onSubmit={submit}>
          <div className="segmented full">
            {DECISIONS.map((d) => (
              <button type="button" key={d.value} className={decision === d.value ? "active" : ""}
                aria-pressed={decision === d.value} onClick={() => setDecision(d.value)}>{d.label}</button>
            ))}
          </div>
          <label>Notes<textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="Why? What did you check?" /></label>
          <label>Your name<input required value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
          <ErrorBox error={error} />
          <button className="btn btn-primary">Record decision</button>
        </form>
      ) : <p className="muted">Available once analysis finishes.</p>}

      {app.reviews.length > 0 && (
        <>
          <h3>History</h3>
          <ul className="reviews">
            {app.reviews.map((r) => (
              <li key={r.id}>
                <StatusPill status={r.decision} /> by <b>{r.reviewer}</b>
                <span className="muted small"> · {new Date(r.created_at).toLocaleString()}</span>
                {r.notes && <p className="small">{r.notes}</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
