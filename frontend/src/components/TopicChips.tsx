import type { TopicWeight } from "../api/types";

export function TopicChips({ topics }: { topics: TopicWeight[] }) {
  if (!topics.length) return null;
  return (
    <div className="topic-chip-list">
      {topics.map((t) => (
        <span className="topic-chip" key={t.topic_id}>
          <span className="dot" />
          {t.label}
          <span className="weight">{Math.round(t.weight * 100)}%</span>
        </span>
      ))}
    </div>
  );
}
