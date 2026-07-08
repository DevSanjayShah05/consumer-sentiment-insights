import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendPoint } from "../api/types";

interface Props {
  trend: TrendPoint[];
  trendB?: TrendPoint[];
  labelA?: string;
  labelB?: string;
  height?: number;
}

/**
 * Monthly sentiment vs. star rating, both expressed on the same [-1, 1]
 * scale (rating normalized as (stars-3)/2, matching the server-side
 * discrepancy formula) so the two measures share a single axis rather than
 * needing a dual-axis chart.
 */
export function TrendChart({ trend, trendB, labelA = "This restaurant", labelB, height = 260 }: Props) {
  interface Row {
    month: string;
    sentiment?: number;
    rating?: number;
    sentimentB?: number;
    ratingB?: number;
  }

  const byMonth = new Map<string, Row>();
  for (const t of trend) {
    byMonth.set(t.month, { month: t.month, sentiment: t.avg_sentiment, rating: (t.avg_stars - 3) / 2 });
  }
  if (trendB) {
    for (const t of trendB) {
      const row: Row = byMonth.get(t.month) ?? { month: t.month };
      row.sentimentB = t.avg_sentiment;
      row.ratingB = (t.avg_stars - 3) / 2;
      byMonth.set(t.month, row);
    }
  }
  const merged = Array.from(byMonth.values()).sort((a, b) => a.month.localeCompare(b.month));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={merged} margin={{ top: 6, right: 16, bottom: 0, left: -18 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "var(--ink-muted)" }}
          axisLine={{ stroke: "var(--axis)" }}
          tickLine={false}
          minTickGap={28}
        />
        <YAxis
          domain={[-1, 1]}
          tick={{ fontSize: 11, fill: "var(--ink-muted)" }}
          axisLine={false}
          tickLine={false}
          width={34}
        />
        <Tooltip
          wrapperStyle={{ outline: "none" }}
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid var(--hairline-strong)",
            borderRadius: 8,
            fontSize: 12.5,
            padding: "8px 12px",
          }}
        />
        <Line
          type="monotone"
          dataKey="sentiment"
          name={`${labelA} · sentiment`}
          stroke="var(--brand)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="rating"
          name={`${labelA} · rating (normalized)`}
          stroke="var(--div-cool)"
          strokeWidth={2}
          strokeDasharray="4 3"
          dot={false}
          isAnimationActive={false}
        />
        {trendB && (
          <>
            <Line
              type="monotone"
              dataKey="sentimentB"
              name={`${labelB} · sentiment`}
              stroke="var(--aspect-service)"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="ratingB"
              name={`${labelB} · rating (normalized)`}
              stroke="var(--aspect-ambiance)"
              strokeWidth={2}
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={false}
            />
          </>
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
