import { useNavigate } from "react-router-dom";
import { DATA_SOURCE_LABELS, type RestaurantCardData } from "../api/types";

interface Props {
  restaurant: RestaurantCardData;
}

function discrepancyBadge(r: RestaurantCardData) {
  const { pct_positive_text_low_star, pct_negative_text_high_star } = r.discrepancy;
  if (pct_positive_text_low_star >= 0.15) {
    return { tone: "warm" as const, label: "Warmer in text than stars" };
  }
  if (pct_negative_text_high_star >= 0.08) {
    return { tone: "cool" as const, label: "Harsher in text than stars" };
  }
  return null;
}

export function RestaurantCard({ restaurant: r }: Props) {
  const navigate = useNavigate();
  const badge = discrepancyBadge(r);

  return (
    <article className="card r-card" onClick={() => navigate(`/restaurant/${r.business_id}`)}>
      <div className="r-card__top">
        <div>
          <div className="r-card__name">{r.name}</div>
          <div className="r-card__loc">{r.city}, {r.state}</div>
        </div>
        <div className="star-badge">
          <strong>{r.avg_stars.toFixed(1)}</strong>
          <span>stars</span>
        </div>
      </div>

      <span className={`source-badge ${r.data_source}`}>
        {DATA_SOURCE_LABELS[r.data_source] ?? r.data_source}
      </span>

      <div className="r-card__categories">
        {r.categories.slice(0, 3).map((c) => (
          <span className="tag" key={c}>{c}</span>
        ))}
      </div>

      <div className="r-card__metrics">
        <div className="metric">
          <span className="value" style={{ color: "var(--brand)" }}>{r.avg_sentiment.toFixed(2)}</span>
          <span className="label">Sentiment</span>
        </div>
        <div className="metric">
          <span className="value">{Math.round(r.pct_positive * 100)}%</span>
          <span className="label">Positive</span>
        </div>
        <div className="metric">
          <span className="value">{r.sampled_reviews}</span>
          <span className="label">Reviews</span>
        </div>
      </div>

      {r.top_topics[0] && (
        <div className="pill" style={{ alignSelf: "flex-start" }}>
          {r.top_topics[0].label}
        </div>
      )}

      <div className="r-card__footer">
        <span style={{ fontSize: 12, color: "var(--ink-muted)" }}>
          {r.data_source === "google_local_reviews" ? "Google" : "Yelp"} {r.platform_stars}★ baseline
        </span>
        {badge && <span className={`discrepancy-note ${badge.tone}`}>{badge.label}</span>}
      </div>
    </article>
  );
}
