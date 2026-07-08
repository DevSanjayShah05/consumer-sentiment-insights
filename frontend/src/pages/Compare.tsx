import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { RestaurantCardData, RestaurantDetail } from "../api/types";
import { AspectBars } from "../components/AspectBars";
import { TrendChart } from "../components/TrendChart";
import { TopicChips } from "../components/TopicChips";

function RestaurantPicker({
  all,
  value,
  onChange,
  placeholder,
}: {
  all: RestaurantCardData[];
  value: string;
  onChange: (id: string) => void;
  placeholder: string;
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} style={{ width: "100%" }}>
      <option value="">{placeholder}</option>
      {all.map((r) => (
        <option key={r.business_id} value={r.business_id}>
          {r.name} — {r.city}, {r.state}
        </option>
      ))}
    </select>
  );
}

function betterLabel(a: number, b: number) {
  if (Math.abs(a - b) < 0.001) return null;
  return a > b ? "a" : "b";
}

export function Compare() {
  const [params, setParams] = useSearchParams();
  const [all, setAll] = useState<RestaurantCardData[]>([]);
  const [idA, setIdA] = useState(params.get("a") ?? "");
  const [idB, setIdB] = useState(params.get("b") ?? "");
  const [a, setA] = useState<RestaurantDetail | null>(null);
  const [b, setB] = useState<RestaurantDetail | null>(null);

  useEffect(() => {
    api.restaurants({ limit: 500, sort: "name", order: "asc" }).then((res) => setAll(res.results));
  }, []);

  useEffect(() => {
    setParams((p) => {
      const next = new URLSearchParams(p);
      idA ? next.set("a", idA) : next.delete("a");
      idB ? next.set("b", idB) : next.delete("b");
      return next;
    }, { replace: true });
    if (idA) api.restaurant(idA).then(setA);
    else setA(null);
    if (idB) api.restaurant(idB).then(setB);
    else setB(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idA, idB]);

  const rows = useMemo(() => {
    if (!a || !b) return [];
    return [
      { label: "Avg. rating", va: a.avg_stars, vb: b.avg_stars, fmt: (v: number) => `${v.toFixed(2)}★` },
      { label: "Computed sentiment", va: a.avg_sentiment, vb: b.avg_sentiment, fmt: (v: number) => v.toFixed(3) },
      { label: "Positive reviews", va: a.pct_positive, vb: b.pct_positive, fmt: (v: number) => `${Math.round(v * 100)}%` },
      { label: "Negative reviews", va: a.pct_negative, vb: b.pct_negative, fmt: (v: number) => `${Math.round(v * 100)}%`, lowerBetter: true },
      { label: "Rating–sentiment gap", va: a.discrepancy.mean_gap, vb: b.discrepancy.mean_gap, fmt: (v: number) => (v >= 0 ? "+" : "") + v.toFixed(2) },
      { label: "Sampled reviews", va: a.sampled_reviews, vb: b.sampled_reviews, fmt: (v: number) => `${v}` },
    ];
  }, [a, b]);

  return (
    <div className="container">
      <section className="page-hero">
        <div className="eyebrow">Side-by-side</div>
        <h1>Compare two restaurants</h1>
        <p className="lede">Line up sentiment, aspect opinion, and topics across two places at once.</p>
      </section>

      <div className="compare-picker">
        <RestaurantPicker all={all} value={idA} onChange={setIdA} placeholder="Choose restaurant A" />
        <span className="vs">vs</span>
        <RestaurantPicker all={all} value={idB} onChange={setIdB} placeholder="Choose restaurant B" />
      </div>

      {!a || !b ? (
        <div className="empty-state">Pick two restaurants to compare.</div>
      ) : (
        <>
          <div className="compare-cols" style={{ marginTop: 28 }}>
            <div className="card compare-col-head">
              <div className="eyebrow">{a.city}, {a.state}</div>
              <h3>{a.name}</h3>
            </div>
            <div className="card compare-col-head">
              <div className="eyebrow">{b.city}, {b.state}</div>
              <h3>{b.name}</h3>
            </div>
          </div>

          <section className="section">
            <div className="section__head">
              <div>
                <h2>Headline metrics</h2>
              </div>
            </div>
            <div className="card" style={{ overflow: "hidden" }}>
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>{a.name}</th>
                    <th>{b.name}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const winner = row.lowerBetter
                      ? betterLabel(row.vb, row.va)
                      : betterLabel(row.va, row.vb);
                    return (
                      <tr key={row.label}>
                        <td>{row.label}</td>
                        <td className={`num ${winner === "a" ? "winner" : ""}`}>{row.fmt(row.va)}</td>
                        <td className={`num ${winner === "b" ? "winner" : ""}`}>{row.fmt(row.vb)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="section">
            <div className="section__head">
              <div>
                <h2>Sentiment over time</h2>
                <p>Both series on the same normalized scale.</p>
              </div>
              <div className="legend-row">
                <span className="item"><span className="swatch" style={{ background: "var(--brand)" }} />{a.name} sentiment</span>
                <span className="item"><span className="swatch" style={{ background: "var(--div-cool)" }} />{a.name} rating</span>
                <span className="item"><span className="swatch" style={{ background: "var(--aspect-service)" }} />{b.name} sentiment</span>
                <span className="item"><span className="swatch" style={{ background: "var(--aspect-ambiance)" }} />{b.name} rating</span>
              </div>
            </div>
            <div className="card chart-panel">
              <TrendChart trend={a.trend} trendB={b.trend} labelA={a.name} labelB={b.name} />
            </div>
          </section>

          <section className="section two-col">
            <div>
              <div className="section__head"><div><h2>{a.name} — aspects</h2></div></div>
              <div className="card chart-panel"><AspectBars aspects={a.aspects} /></div>
            </div>
            <div>
              <div className="section__head"><div><h2>{b.name} — aspects</h2></div></div>
              <div className="card chart-panel"><AspectBars aspects={b.aspects} /></div>
            </div>
          </section>

          <section className="section two-col">
            <div>
              <div className="section__head"><div><h2>{a.name} — topics</h2></div></div>
              <div className="card chart-panel"><TopicChips topics={a.top_topics} /></div>
            </div>
            <div>
              <div className="section__head"><div><h2>{b.name} — topics</h2></div></div>
              <div className="card chart-panel"><TopicChips topics={b.top_topics} /></div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
