import type { Criterion } from "../types";

interface Props {
  value: Criterion[];
  onChange: (next: Criterion[]) => void;
  /** When true, labels are read-only; only weights and must-have flags can change. */
  weightsOnly?: boolean;
}

export default function CriteriaEditor({ value, onChange, weightsOnly = false }: Props) {
  const update = (i: number, patch: Partial<Criterion>) =>
    onChange(value.map((c, j) => (j === i ? { ...c, ...patch } : c)));

  return (
    <div className="criteria-editor">
      <div className="criteria-row criteria-head">
        <span>Criterion</span>
        <span>Weight</span>
        <span>Must-have</span>
        <span />
      </div>
      {value.map((c, i) => (
        <div className="criteria-row" key={c.key ?? i}>
          {weightsOnly ? (
            <span>{c.label}</span>
          ) : (
            <input
              aria-label="Criterion"
              placeholder="e.g. Python in production (3+ years)"
              value={c.label}
              onChange={(e) => update(i, { label: e.target.value })}
            />
          )}
          <span className="weight-cell">
            <input
              type="range" min={0} max={5} step={0.5} value={c.weight}
              aria-label={`Weight for ${c.label}`}
              onChange={(e) => update(i, { weight: Number(e.target.value) })}
            />
            <span className="weight-value">{c.weight}</span>
          </span>
          <input
            type="checkbox" checked={c.must_have}
            aria-label={`${c.label} is must-have`}
            onChange={(e) => update(i, { must_have: e.target.checked })}
          />
          {weightsOnly ? <span /> : (
            <button type="button" className="btn-icon" aria-label="Remove criterion"
              onClick={() => onChange(value.filter((_, j) => j !== i))} disabled={value.length <= 1}>
              ×
            </button>
          )}
        </div>
      ))}
      {!weightsOnly && (
        <button type="button" className="btn btn-ghost"
          onClick={() => onChange([...value, { label: "", weight: 1, must_have: false }])}>
          + Add criterion
        </button>
      )}
    </div>
  );
}
