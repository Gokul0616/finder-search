"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "@/context/ThemeContext";
import SearchBar from "@/components/SearchBar";
import { searchService } from "@/lib/services";
import { StatsResponse } from "@/types";
import styles from "./page.module.css";
import Link from "next/link";

export default function HomePage() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const [query, setQuery] = useState("");
  const [stats, setStats] = useState<StatsResponse | null>(null);

  useEffect(() => {
    searchService
      .getStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  const handleSearch = (q: string) => {
    if (q.trim()) {
      router.push(`/search?q=${encodeURIComponent(q.trim())}`);
    }
  };

  return (
    <div className={styles.page}>
      {/* Top Navigation */}
      <nav className={styles.nav}>
        <div className={styles.navInner}>
          <Link href="/" className={styles.logoCluster}>
            <svg className={styles.spike} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="12" y1="2" x2="12" y2="22" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <line x1="5" y1="5" x2="19" y2="19" />
              <line x1="19" y1="5" x2="5" y2="19" />
            </svg>
            <span className={styles.logoText}>Finder</span>
          </Link>
          <div className={styles.navLinks}>
            <a href="#features" className={styles.navLink}>Technology</a>
            <a href="#code" className={styles.navLink}>Developer</a>
            <a href="#pricing" className={styles.navLink}>Pricing</a>
          </div>
          <div className={styles.navRight}>
            <button
              className={styles.themeBtn}
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>
            <button className={styles.navBtn} onClick={() => handleSearch("wikipedia")}>Try Search</button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <header className={styles.hero}>
        <div className={styles.heroLeft}>
          <h1 className={styles.heroTitle}>Search the web with intelligence.</h1>
          <p className={styles.heroSubtitle}>
            A modern, Python-powered search engine built from scratch. Crawl directories, build linkage graphs, rank using PageRank + BM25, and search results instantly.
          </p>
          <div className={styles.heroSearchWrapper}>
            <SearchBar
              value={query}
              onChange={setQuery}
              onSubmit={handleSearch}
              variant="large"
              autoFocus
            />
          </div>
          <span className={styles.kbdHint}>
            Press <kbd className={styles.kbd}>/</kbd> to focus the search bar
          </span>
        </div>

        {/* Dashboard/Mockup Card */}
        <div className={styles.mockup}>
          <div className={styles.mockupHeader}>
            <span className={styles.mockupTitle}>System Monitor</span>
            <span className={styles.mockupBadge}>Atlas Active</span>
          </div>
          <div className={styles.mockupBody}>
            <div className={styles.mockupRow}>
              <span className={styles.mockupKey}>Database status</span>
              <span className={styles.mockupVal} style={{ color: "var(--text-url)" }}>Online</span>
            </div>
            <div className={styles.mockupRow}>
              <span className={styles.mockupKey}>Crawled Pages</span>
              <span className={styles.mockupVal}>{stats?.crawled_pages?.toLocaleString() || "133"}</span>
            </div>
            <div className={styles.mockupRow}>
              <span className={styles.mockupKey}>Total Outbound Links</span>
              <span className={styles.mockupVal}>{stats?.total_links?.toLocaleString() || "26,962"}</span>
            </div>
            <div className={styles.mockupRow}>
              <span className={styles.mockupKey}>Unique Domains</span>
              <span className={styles.mockupVal}>{stats?.unique_domains?.toLocaleString() || "27"}</span>
            </div>
            <div className={styles.mockupRow}>
              <span className={styles.mockupKey}>Search Mode</span>
              <span className={styles.mockupVal}>Atlas Inverted Index</span>
            </div>
          </div>
        </div>
      </header>

      {/* Feature Cards Section */}
      <section id="features" className={styles.features}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Built on a Three-Tier Pipeline</h2>
          <p className={styles.sectionDesc}>How Finder crawls, parses, indexes, and queries the web corpus.</p>
        </div>
        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🕷️</div>
            <h3>1. Async Crawler</h3>
            <p>
              Driven by httpx and BeautifulSoup. Respects robots.txt directives, conforms to rate limits, and persists raw HTML in gzip compressed storage.
            </p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🕸️</div>
            <h3>2. Link Graph & PageRank</h3>
            <p>
              Constructs a directed graph of all domain linkages. Computes eigenvector centrality using standard PageRank to weight authority.
            </p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🗂️</div>
            <h3>3. Dual Index Search</h3>
            <p>
              Leverages text tokenizers, stemming, and fallback search modes, combining BM25 relevance with PageRank metrics for final scoring.
            </p>
          </div>
        </div>
      </section>

      {/* Code Mockup Section */}
      <section id="code" className={styles.codeSection}>
        <div className={styles.codeBlockText}>
          <h2 className={styles.sectionTitle}>Simple and Extensible Architecture</h2>
          <p className={styles.sectionDesc} style={{ color: "var(--text-secondary)" }}>
            Engineered with modern Python and Next.js. Easily inspect PageRank calculation scripts or scale the indexer using configuration environment variables.
          </p>
        </div>
        <div className={styles.codeWindow}>
          <div className={styles.codeHeader}>
            <div className={styles.codeDot} />
            <div className={styles.codeDot} />
            <div className={styles.codeDot} />
            <span className={styles.codeTitle}>finder/graph/pagerank.py</span>
          </div>
          <pre>
            <code>
              <span className={styles.keyword}>async def</span> <span className={styles.function}>compute_pagerank</span>(alpha: <span className={styles.keyword}>float</span> = <span className={styles.string}>0.85</span>):<br />
              &nbsp;&nbsp;&nbsp;&nbsp;<span className={styles.comment}># Build the link graph from MongoDB documents</span><br />
              &nbsp;&nbsp;&nbsp;&nbsp;G = <span className={styles.keyword}>await</span> build_link_graph()<br /><br />
              &nbsp;&nbsp;&nbsp;&nbsp;<span className={styles.comment}># Run iterative PageRank convergence</span><br />
              &nbsp;&nbsp;&nbsp;&nbsp;scores = nx.pagerank(G, alpha=alpha)<br />
              &nbsp;&nbsp;&nbsp;&nbsp;<span className={styles.keyword}>await</span> crud.update_pagerank_scores(scores)
            </code>
          </pre>
        </div>
      </section>

      {/* Pricing Tiers Section */}
      <section id="pricing" className={styles.pricing}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Simple Pricing Plans</h2>
          <p className={styles.sectionDesc}>Choose a plan that fits your search scale.</p>
        </div>
        <div className={styles.pricingGrid}>
          <div className={styles.pricingCard}>
            <div className={styles.pricingHeader}>
              <h3>Free Plan</h3>
              <div className={styles.price}>$0<span className={styles.priceSub}>/month</span></div>
            </div>
            <ul className={styles.featuresList}>
              <li>Search all crawls</li>
              <li>PageRank rankings</li>
              <li>Snippets & Highlights</li>
            </ul>
            <button className={styles.pricingBtn} onClick={() => handleSearch("pagerank")}>Start Searching</button>
          </div>

          <div className={`${styles.pricingCard} ${styles.pricingCardFeatured}`}>
            <div className={styles.pricingHeader}>
              <h3>Developer Pro</h3>
              <div className={styles.price}>$20<span className={styles.priceSub} style={{ color: "#a09d96" }}>/month</span></div>
            </div>
            <ul className={styles.featuresList}>
              <li>Full REST API Access</li>
              <li>Custom crawl job trigger</li>
              <li>Up to 100K indexed pages</li>
              <li>Prioritized seed priority queue</li>
            </ul>
            <button className={`${styles.pricingBtn} ${styles.pricingBtnFeatured}`} onClick={() => handleSearch("wikipedia")}>Get Developer API</button>
          </div>

          <div className={styles.pricingCard}>
            <div className={styles.pricingHeader}>
              <h3>Enterprise</h3>
              <div className={styles.price}>Custom</div>
            </div>
            <ul className={styles.featuresList}>
              <li>Dedicated crawl nodes</li>
              <li>Custom semantic extraction</li>
              <li>Continuous live updates</li>
              <li>Dedicated support SLA</li>
            </ul>
            <button className={styles.pricingBtn} onClick={() => handleSearch("crawler")}>Contact Sales</button>
          </div>
        </div>
      </section>

      {/* Pre-footer Coral CTA Band */}
      <section className={styles.ctaBand}>
        <h2>Start crawling the web graph</h2>
        <p>Run your own async crawlers, execute PageRank mathematical matrices, and search results instantly using Finder.</p>
        <button className={styles.ctaBtn} onClick={() => handleSearch("algorithm")}>Search "algorithm"</button>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <Link href="/" className={styles.logoCluster}>
              <svg className={styles.spike} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="12" y1="2" x2="12" y2="22" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <line x1="5" y1="5" x2="19" y2="19" />
                <line x1="19" y1="5" x2="5" y2="19" />
              </svg>
              <span className={styles.logoText}>Finder</span>
            </Link>
            <p>A web crawler, graph engine, and semantic search interface built completely from scratch.</p>
          </div>
          <div className={styles.footerCol}>
            <h4>Product</h4>
            <ul className={styles.footerLinks}>
              <li><a href="#features">Features</a></li>
              <li><a href="#code">Developer API</a></li>
              <li><a href="#pricing">Pricing</a></li>
            </ul>
          </div>
          <div className={styles.footerCol}>
            <h4>Resources</h4>
            <ul className={styles.footerLinks}>
              <li><a href="https://github.com/Gokul0616/finder-search" target="_blank" rel="noopener noreferrer">GitHub Repo</a></li>
              <li><a href="/docs" onClick={(e) => { e.preventDefault(); alert("API Docs: http://localhost:8000/docs"); }}>Docs API</a></li>
            </ul>
          </div>
          <div className={styles.footerCol}>
            <h4>Company</h4>
            <ul className={styles.footerLinks}>
              <li><a href="#" onClick={(e) => e.preventDefault()}>About Us</a></li>
              <li><a href="#" onClick={(e) => e.preventDefault()}>Research</a></li>
            </ul>
          </div>
        </div>
        <div className={styles.footerBottom}>
          <span>&copy; {new Date().getFullYear()} Finder Search Engine. All rights reserved.</span>
          <span>Built for the Gokul0616/finder-search showcase.</span>
        </div>
      </footer>
    </div>
  );
}
