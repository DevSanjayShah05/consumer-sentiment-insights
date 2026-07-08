import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { RestaurantDetail as RestaurantDetailType } from "../api/types";
import { AspectBars } from "../components/AspectBars";
import { PullQuote } from "../components/PullQuote";
import { TopicChips } from "../components/TopicChips";
import { TrendChart } from "../components/TrendChart";

export function RestaurantDetail() {
  const { id } = useParams<{ id: string }>();
  const [r, setR] = useState<RestaurantDetailType | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    setR(null);
    setError(false);
    api.restaurant(id).catch(() => setError(true)).then((res) => res && setR(res));
  }, [id]);

  if (error) {
    return (
      <div className="container">
        <div className="empty-state">
          Couldn&apos;t find that restaurant. <Link to="/" style={{ color: "var(--brand)" }}>Back to explorer</Link>
        </div>
      </div>
    );
  }

  if (!r) {
    return (
      <div className="container">
        <div className="loading-state">Loading restaurant…</div>
      </div>
    );
  }

  const gap = r.discrepancy.mean_gap;

  return (
    <div className="container">
      <div className="detail-header">
        <Link to="/" className="back-link">← Back to explorer</Link>
        <div className="detail-header__top">
          <div>
            <div className="eyebrow">{r.city}, {r.state} · {r.categories.slice(0, 4).join(" · ")}</div>
            <h1>{r.name}</h1>
          </div>
          <Link to={`/compare?a=${r.business_id}`} className="btn secondary">Compare this restaurant</Link>
        </div>
      </div>

      <div className="kpi-row">
        <div className="kpi-tile">
          <div className="eyebrow">Avg. rating</div>
          <div className="value">{r.avg_stars.toFixed(2)}★</div>
          <div className="sub">Yelp baseline {r.yelp_stars}★</div>
        </div>
        <div className="kpi-tile">
          <div className="eyebrow">Computed sentiment</div>
          <div className="value" style={{ color: "var(--brand)" }}>{r.avg_sentiment.toFixed(2)}</div>
          <div className="sub">VADER compound, [-1, 1]</div>
        </div>
        <div className="kpi-tile">
          <div className="eyebrow">Positive reviews</div>
          <div className="value">{Math.round(r.pct_positive * 100)}%</div>
          <div className="sub">{Math.round(r.pct_negative * 100)}% negative</div>
        </div>
        <div className="kpi-tile">
          <div className="eyebrow">Rating–sentiment gap</div>
          <div className="value" style={{ color: gap >= 0 ? "var(--div-warm)" : "var(--div-cool)" }}>
            {gap >= 0 ? "+" : ""}{gap.toFixed(2)}
          </div>
          <div className="sub">{gap >= 0 ? "Text warmer than stars" : "Text harsher than stars"}</div>
        </div>
        <div className="kpi-tile">
          <div className="eyebrow">Sampled reviews</div>
          <div className="value">{r.sampled_reviews}</div>
          <div className="sub">{r.first_review} → {r.last_review}</div>
        </div>
      </div>

      <section className="section">
        <div className="section__head">
          <div>
            <h2>Sentiment over time</h2>
            <p>Monthly average, sentiment vs. star rating (normalized to the same −1…1 scale).</p>
          </div>
          <div className="legend-row">
            <span className="item"><span className="swatch" style={{ background: "var(--brand)" }} />Sentiment</span>
            <span className="item"><span className="swatch" style={{ background: "var(--div-cool)" }} />Rating (normalized)</span>
          </div>
        </div>
        <div className="card chart-panel">
          <TrendChart trend={r.trend} />
        </div>
      </section>

      <section className="section two-col">
        <div>
          <div className="section__head">
            <div>
              <h2>Aspect sentiment</h2>
              <p>Keyword-anchored sentence-level sentiment, per aspect.</p>
            </div>
          </div>
          <div className="card chart-panel">
            <AspectBars aspects={r.aspects} />
          </div>
        </div>
        <div>
          <div className="section__head">
            <div>
              <h2>What they talk about</h2>
              <p>Dominant LDA topics among this restaurant&apos;s reviews.</p>
            </div>
          </div>
          <div className="card chart-panel">
            <TopicChips topics={r.top_topics} />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section__head">
          <div>
            <h2>Review highlights</h2>
            <p>Representative pull-quotes at the extremes of computed sentiment.</p>
          </div>
        </div>
        <div className="quote-grid">
          {r.highlights.positive.map((q, i) => (
            <PullQuote quote={q} tone="positive" key={`p${i}`} />
          ))}
          {r.highlights.negative.map((q, i) => (
            <PullQuote quote={q} tone="negative" key={`n${i}`} />
          ))}
        </div>
      </section>
    </div>
  );
}
