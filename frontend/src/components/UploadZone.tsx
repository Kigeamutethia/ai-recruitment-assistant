import { useRef, useState } from "react";
import { api } from "../api";
import type { UploadResult } from "../types";

export default function UploadZone({ jobId, onUploaded }: { jobId: string; onUploaded: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function upload(list: FileList | null) {
    const files = Array.from(list ?? []);
    if (!files.length) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.uploadCvs(jobId, files));
      onUploaded();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div>
      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files); }}
        onClick={() => input.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      >
        <input ref={input} type="file" accept="application/pdf,.pdf" multiple hidden
          onChange={(e) => upload(e.target.files)} />
        <strong>{busy ? "Uploading…" : "Drop PDF CVs here"}</strong>
        <span className="muted">or click to choose files · PDF only, multiple allowed</span>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {result && (
        <div className="alert alert-info">
          {result.accepted.length} CV(s) queued for analysis.
          {result.rejected.length > 0 && (
            <ul>
              {result.rejected.map((r) => <li key={r.filename}><b>{r.filename}</b>: {r.reason}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
