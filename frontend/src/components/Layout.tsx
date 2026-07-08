import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="site-header">
        <div className="container site-header__inner">
          <NavLink to="/" className="brand">
            <span className="brand__mark">Tablecloth</span>
            <span className="brand__tagline">Consumer review &amp; sentiment intelligence</span>
          </NavLink>
          <nav className="site-nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
              Explorer
            </NavLink>
            <NavLink to="/compare" className={({ isActive }) => (isActive ? "active" : "")}>
              Compare
            </NavLink>
          </nav>
        </div>
      </header>
      <main style={{ flex: 1 }}>{children}</main>
      <footer className="site-footer">
        <div className="container">
          Tablecloth is a portfolio analytics project built on a sampled, processed slice of the
          Yelp Open Dataset. Sentiment, aspects, topics and discrepancy scores are model estimates,
          not verified facts about any business. See the README for data sources and methodology.
        </div>
      </footer>
    </>
  );
}
