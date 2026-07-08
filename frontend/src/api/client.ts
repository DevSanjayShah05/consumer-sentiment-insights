import type {
  FiltersInfo,
  GeoRow,
  MetaInfo,
  Paginated,
  RestaurantCardData,
  RestaurantDetail,
  ReviewRecord,
  Topic,
  TrendPoint,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

async function getJSON<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(BASE_URL + path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString().replace(window.location.origin, ""));
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}): ${path}`);
  }
  return res.json() as Promise<T>;
}

export interface RestaurantListParams {
  city?: string;
  state?: string;
  category?: string;
  data_source?: string;
  min_stars?: number;
  min_sentiment?: number;
  discrepancy?: string;
  sort?: string;
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export const api = {
  meta: () => getJSON<MetaInfo>("/meta"),
  filters: () => getJSON<FiltersInfo>("/filters"),
  topics: () => getJSON<Topic[]>("/topics"),
  restaurants: (params: RestaurantListParams = {}) =>
    getJSON<Paginated<RestaurantCardData>>("/restaurants", { ...params }),
  restaurant: (id: string) => getJSON<RestaurantDetail>(`/restaurants/${encodeURIComponent(id)}`),
  restaurantReviews: (id: string, params: { limit?: number; offset?: number; flag?: string } = {}) =>
    getJSON<Paginated<ReviewRecord>>(`/restaurants/${encodeURIComponent(id)}/reviews`, { ...params }),
  compare: (a: string, b: string) =>
    getJSON<{ a: RestaurantDetail; b: RestaurantDetail }>("/compare", { a, b }),
  geo: () => getJSON<GeoRow[]>("/geo"),
  trend: () => getJSON<TrendPoint[]>("/trend"),
};
