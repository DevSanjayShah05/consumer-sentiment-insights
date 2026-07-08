import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import type { TrendPoint } from "../api/types";

interface Props {
  trend: TrendPoint[];
  height?: number;
}

/** Compact single-series sentiment sparkline for restaurant cards. */
export function Sparkline({ trend, height = 44 }: Props) {
  if (!trend || trend.length < 2) {
    return <div style={{ height, display: "flex", alignItems: "center", fontSize: 11, color: "var(--ink-muted)" }}>Not enough history</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={trend} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
        <defs>
          <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--seq-500)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--seq-500)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <YAxis domain={[-1, 1]} hide />
        <Area
          type="monotone"
          dataKey="avg_sentiment"
          stroke="var(--seq-500)"
          strokeWidth={2}
          fill="url(#sparkFill)"
          isAnimationActive={false}
        />
        <Tooltip
          wrapperStyle={{ outline: "none" }}
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid var(--hairline-strong)",
            borderRadius: 8,
            fontSize: 12,
            padding: "6px 10px",
          }}
          formatter={(v) => [Number(v).toFixed(2), "Sentiment"]}
          labelFormatter={(l) => l}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
