"use client";

import React, { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Header from "@/components/Header";
import ResultCard from "@/components/ResultCard";
import Pagination from "@/components/Pagination";
import { searchService } from "@/lib/services";
import { SearchResponse } from "@/types";
import styles from "./page.module.css";

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const queryParam = searchParams.get("q") || "";
  const pageParam = parseInt(searchParams.get("page") || "1", 10);

  const [query, setQuery] = useState(queryParam);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doSearch = useCallback(
    async (q: string, page: number) => {
      if (!q.trim()) return;

      setIsLoading(true);
      setError(null);

      try {
        const result = await searchService.search(q, page);
        setData(result);
      } catch (err: any) {
        if (err.request && !err.response) {
          setError(
            "Cannot connect to the search backend. Make sure the API server is running on port 8000."
          );
        } else {
          setError(err.message || "Something went wrong");
        }
        setData(null);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (queryParam) {
      setQuery(queryParam);
      doSearch(queryParam, pageParam);
    }
  }, [queryParam, pageParam, doSearch]);

  const handleSearch = (q: string) => {
    router.push(`/search?q=${encodeURIComponent(q.trim())}`);
  };

  const handlePageChange = (page: number) => {
    router.push(
      `/search?q=${encodeURIComponent(queryParam)}&page=${page}`
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className={styles.page}>
      <Header query={query} onQueryChange={setQuery} onSearch={handleSearch} />

      <main className={styles.main}>
        <div className={styles.container}>
          {/* Results meta */}
          {data && !isLoading && (
            <p className={styles.meta}>
              About {data.total.toLocaleString()} results ({data.took_ms.toFixed(0)} ms)
            </p>
          )}

          {/* Loading */}
          {isLoading && (
            <div className={styles.loading}>
              <div className={styles.loadingDots}>
                <span />
                <span />
                <span />
              </div>
              <p>Searching...</p>
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className={styles.stateBlock}>
              <div className={styles.stateIcon}>⚠️</div>
              <h2>Something went wrong</h2>
              <p className={styles.stateText}>{error}</p>
            </div>
          )}

          {/* Empty */}
          {data && data.results.length === 0 && !isLoading && (
            <div className={styles.stateBlock}>
              <div className={styles.stateIcon}>🔎</div>
              <h2>No results found</h2>
              <p className={styles.stateText}>
                Try different keywords or check your spelling.
              </p>
            </div>
          )}

          {/* Results */}
          {data && data.results.length > 0 && !isLoading && (
            <>
              <div className={styles.resultsList}>
                {data.results.map((result, i) => (
                  <ResultCard key={result.url} result={result} index={i} />
                ))}
              </div>

              <Pagination
                currentPage={data.page}
                totalPages={data.total_pages}
                onPageChange={handlePageChange}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div style={{ padding: "60px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading...
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
