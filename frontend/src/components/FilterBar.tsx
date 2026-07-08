import { DATA_SOURCE_LABELS, type FiltersInfo } from "../api/types";
import type { RestaurantListParams } from "../api/client";

interface Props {
  filters: FiltersInfo | null;
  value: RestaurantListParams;
  onChange: (next: RestaurantListParams) => void;
  total: number;
}

export function FilterBar({ filters, value, onChange, total }: Props) {
  return (
    <div className="filter-bar">
      <select
        value={value.state ?? ""}
        onChange={(e) => onChange({ ...value, state: e.target.value || undefined, city: undefined })}
      >
        <option value="">All states</option>
        {filters?.states.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <select
        value={value.category ?? ""}
        onChange={(e) => onChange({ ...value, category: e.target.value || undefined })}
      >
        <option value="">All cuisines</option>
        {filters?.categories.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      <select
        value={value.data_source ?? ""}
        onChange={(e) => onChange({ ...value, data_source: e.target.value || undefined })}
      >
        <option value="">All sources</option>
        {filters?.data_sources.map((s) => (
          <option key={s} value={s}>{DATA_SOURCE_LABELS[s] ?? s}</option>
        ))}
      </select>

      <select
        value={value.sort ?? "sampled_reviews"}
        onChange={(e) => onChange({ ...value, sort: e.target.value })}
      >
        <option value="sampled_reviews">Most reviewed</option>
        <option value="avg_sentiment">Highest sentiment</option>
        <option value="avg_stars">Highest rating</option>
        <option value="name">Name (A–Z)</option>
      </select>

      <button
        type="button"
        className={`filter-chip-toggle ${value.discrepancy === "positive_text_low_star" ? "active" : ""}`}
        onClick={() =>
          onChange({
            ...value,
            discrepancy: value.discrepancy === "positive_text_low_star" ? undefined : "positive_text_low_star",
          })
        }
      >
        Hidden gems (warm text, low stars)
      </button>

      <button
        type="button"
        className={`filter-chip-toggle ${value.discrepancy === "negative_text_high_star" ? "active" : ""}`}
        onClick={() =>
          onChange({
            ...value,
            discrepancy: value.discrepancy === "negative_text_high_star" ? undefined : "negative_text_high_star",
          })
        }
      >
        Overrated (harsh text, high stars)
      </button>

      <span className="result-count">{total.toLocaleString()} restaurants</span>
    </div>
  );
}
