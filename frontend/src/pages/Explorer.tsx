import { useEffect, useState } from "react";
import { api, type RestaurantListParams } from "../api/client";
import type { FiltersInfo, MetaInfo, RestaurantCardData } from "../api/types";
import { FilterBar } from "../components/FilterBar";
import { RestaurantCard } from "../components/RestaurantCard";

export function Explorer() {
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [filters, setFilters] = useState<FiltersInfo | null>(null);
  const [params, setParams] = useState<RestaurantListParams>({ sort: "sampled_reviews", limit: 30 });
  const [results, setResults] = useState<RestaurantCardData[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.filters().then(setFilters).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .restaurants(params)
      .then((res) => {
        setResults(res.results);
        setTotal(res.total);
      })
      .finally(() => setLoading(false));
  }, [params]);

  return (
    <div className="container">
      <section className="page-hero">
        <div className="eyebrow">Consumer insights · Restaurants</div>
        <h1>What diners actually say, beneath the star rating.</h1>
        <p className="lede">
          Tablecloth mines {meta ? meta.reviews.toLocaleString() : "tens of thousands of"} real
          reviews across {meta ? meta.restaurants.toLocaleString() : "hundreds of"} restaurants to
          surface sentiment trends, aspect-level opinion on food, service, price and ambiance, the
          themes people write about, and the places where the star rating and the text disagree.
        </p>
      </section>

      <FilterBar filters={filters} value={params} onChange={(p) => setParams({ ...p, offset: 0 })} total={total} />

      {loading ? (
        <div className="loading-state">Loading restaurants…</div>
      ) : results.length === 0 ? (
        <div className="empty-state">No restaurants match those filters.</div>
      ) : (
        <div className="restaurant-grid">
          {results.map((r) => (
            <RestaurantCard restaurant={r} key={r.business_id} />
          ))}
        </div>
      )}
    </div>
  );
}
