export type AspectKey = "food" | "service" | "price" | "ambiance";

export interface AspectSummary {
  score: number | null;
  coverage: number;
}

export interface TrendPoint {
  month: string;
  avg_sentiment: number;
  avg_stars: number;
  count: number;
}

export interface TopicWeight {
  topic_id: number;
  label: string;
  weight: number;
}

export interface Topic {
  topic_id: number;
  label: string;
  top_terms: string[];
  review_count: number;
}

export interface DiscrepancySummary {
  mean_gap: number;
  pct_positive_text_low_star: number;
  pct_negative_text_high_star: number;
}

export interface HighlightQuote {
  text: string;
  stars: number;
  sentiment: number;
  date: string;
}

export interface Highlights {
  positive: HighlightQuote[];
  negative: HighlightQuote[];
}

export interface RestaurantCardData {
  business_id: string;
  name: string;
  city: string;
  state: string;
  categories: string[];
  yelp_stars: number;
  avg_stars: number;
  avg_sentiment: number;
  pct_positive: number;
  pct_negative: number;
  sampled_reviews: number;
  top_topics: TopicWeight[];
  discrepancy: DiscrepancySummary;
}

export interface RestaurantDetail extends RestaurantCardData {
  postal_code: string;
  latitude: number;
  longitude: number;
  yelp_review_count: number;
  first_review: string;
  last_review: string;
  aspects: Record<AspectKey, AspectSummary>;
  trend: TrendPoint[];
  highlights: Highlights;
}

export interface ReviewRecord {
  review_id: string;
  business_id: string;
  date: string;
  stars: number;
  sentiment: number;
  sentiment_label: "positive" | "neutral" | "negative";
  discrepancy: number;
  discrepancy_flag: "positive_text_low_star" | "negative_text_high_star" | null;
  topic_id: number;
  useful: number;
  aspect_food: number | null;
  aspect_service: number | null;
  aspect_price: number | null;
  aspect_ambiance: number | null;
  text: string;
}

export interface Paginated<T> {
  total: number;
  limit: number;
  offset: number;
  results: T[];
}

export interface GeoRow {
  city: string;
  state: string;
  restaurants: number;
  avg_sentiment: number;
  avg_stars: number;
  latitude: number;
  longitude: number;
}

export interface MetaInfo {
  source: string;
  business_source: string;
  review_source: string;
  restaurants: number;
  reviews: number;
  cities: number;
  states: number;
  date_range: [string, string];
  sentiment_model: string;
  topic_model: string;
  aspects: string[];
  sampling: Record<string, number>;
}

export interface FiltersInfo {
  cities: string[];
  states: string[];
  categories: string[];
}
