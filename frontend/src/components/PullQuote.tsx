import type { HighlightQuote } from "../api/types";

interface Props {
  quote: HighlightQuote;
  tone: "positive" | "negative";
}

export function PullQuote({ quote, tone }: Props) {
  return (
    <div className={`card pull-quote ${tone}`}>
      <p className="quote-text">{quote.text}</p>
      <div className="quote-meta">
        <span>{quote.stars.toFixed(0)}★ review · {quote.date}</span>
        <span style={{ color: tone === "positive" ? "var(--status-good)" : "var(--div-cool)" }}>
          sentiment {quote.sentiment.toFixed(2)}
        </span>
      </div>
    </div>
  );
}
