"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "@/context/ThemeContext";
import SearchBar from "@/components/SearchBar";
import { searchService } from "@/lib/services";
import { StatsResponse } from "@/types";
import styles from "./page.module.css";

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
      {/* Theme toggle — top right */}
      <div className={styles.topBar}>
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
      </div>

      {/* Centered content */}
      <main className={styles.center}>
        <div className={styles.logoBlock}>
          <h1 className={styles.logo}>
            <svg className={styles.spike} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="12" y1="2" x2="12" y2="22" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <line x1="5" y1="5" x2="19" y2="19" />
              <line x1="19" y1="5" x2="5" y2="19" />
            </svg>
            <span className={styles.logoText}>Finder</span>
          </h1>
        </div>

        <SearchBar
          value={query}
          onChange={setQuery}
          onSubmit={handleSearch}
          variant="large"
          autoFocus
        />

        {stats && stats.crawled_pages > 0 && (
          <p className={styles.stats}>
            Searching across{" "}
            <strong>{stats.crawled_pages.toLocaleString()}</strong> pages from{" "}
            <strong>{stats.unique_domains.toLocaleString()}</strong> domains
          </p>
        )}
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerRow}>
          <span>Built from scratch</span>
          <span>·</span>
          <span>Crawl → Index → Rank → Search</span>
        </div>
      </footer>
    </div>
  );
}
