import type { AspectKey, AspectSummary } from "../api/types";

const ASPECT_META: Record<AspectKey, { label: string; color: string }> = {
  food: { label: "Food", color: "var(--aspect-food)" },
  service: { label: "Service", color: "var(--aspect-service)" },
  price: { label: "Price", color: "var(--aspect-price)" },
  ambiance: { label: "Ambiance", color: "var(--aspect-ambiance)" },
};

const ORDER: AspectKey[] = ["food", "service", "price", "ambiance"];

interface Props {
  aspects: Record<AspectKey, AspectSummary>;
  compareAspects?: Record<AspectKey, AspectSummary>;
}

/**
 * Direct-labeled horizontal bar rows for the four tracked aspects. Bars are
 * plain HTML/CSS (not a chart library) so every value gets a visible label,
 * satisfying the CVD-floor requirement for a 4-series categorical set.
 */
export function AspectBars({ aspects }: Props) {
  return (
    <div>
      {ORDER.map((key) => {
        const a = aspects[key];
        const meta = ASPECT_META[key];
        const score = a?.score ?? null;
        const pct = score === null ? 0 : ((score + 1) / 2) * 100;
        return (
          <div className="aspect-bar-row" key={key}>
            <div>
              <div className="name">{meta.label}</div>
              {a && <div className="aspect-coverage">{Math.round(a.coverage * 100)}% of reviews</div>}
            </div>
            <div className="aspect-bar-track">
              {score !== null && (
                <div
                  className="aspect-bar-fill"
                  style={{ left: 0, width: `${pct}%`, background: meta.color }}
                />
              )}
            </div>
            <div className="score" style={{ color: score === null ? "var(--ink-muted)" : meta.color }}>
              {score === null ? "—" : score.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export { ASPECT_META, ORDER as ASPECT_ORDER };
