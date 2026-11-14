import type { AppStatus } from "../types";

const STATUS_LABEL: Record<AppStatus, string> = {
  received: "Queued",
  processing: "Analysing…",
  analysed: "Awaiting review",
  failed: "Failed",
  shortlisted: "Shortlisted",
  on_hold: "On hold",
  not_progressing: "Not progressing",
};

export function StatusPill({ status }: { status: AppStatus }) {
  return <span className={`pill pill-${status}`}>{STATUS_LABEL[status]}</span>;
}

export function scoreBand(score: number) {
  return score >= 70 ? "high" : score >= 45 ? "mid" : "low";
}

export function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span className="muted">—</span>;
  return (
    <span className="scorebar" title={`${score.toFixed(1)} / 100`}>
      <span className="scorebar-track">
        <span className={`scorebar-fill band-${scoreBand(score)}`} style={{ width: `${score}%` }} />
      </span>
      <span className="scorebar-value">{Math.round(score)}</span>
    </span>
  );
}

/** 0–5 criterion score as five dots. */
export function Dots({ score }: { score: number }) {
  return (
    <span className="dots" aria-label={`${score} out of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`dot ${i <= score ? "on" : ""}`} />
      ))}
      <span className="dots-value">{score}/5</span>
    </span>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  return error ? <div className="alert alert-error" role="alert">{error}</div> : null;
}
