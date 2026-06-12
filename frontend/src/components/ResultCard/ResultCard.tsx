import React from "react";
import { SearchResultItem } from "@/types";
import styles from "./ResultCard.module.css";

interface ResultCardProps {
  result: SearchResultItem;
  index: number;
}

export default function ResultCard({ result, index }: ResultCardProps) {
  const domain = result.domain || (() => {
    try { return new URL(result.url).hostname; } catch { return ""; }
  })();

  const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;

  return (
    <article
      className={styles.card}
      style={{ animationDelay: `${index * 0.04}s` }}
    >
      <div className={styles.urlRow}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className={styles.favicon}
          src={faviconUrl}
          alt=""
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
        <span className={styles.site}>{domain}</span>
      </div>

      <a
        className={styles.url}
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        {decodeURIComponent(result.url)}
      </a>

      <h2 className={styles.title}>
        <a href={result.url} target="_blank" rel="noopener noreferrer">
          {result.title}
        </a>
      </h2>

      <p
        className={styles.snippet}
        dangerouslySetInnerHTML={{ __html: result.snippet }}
      />

      <div className={styles.meta}>
        <span className={styles.scoreBadge} title="Combined relevance + authority score">
          ⚡ {result.score.toFixed(3)}
        </span>
        <span title="BM25 text relevance">
          Relevance: {result.bm25_score.toFixed(3)}
        </span>
        <span title="PageRank authority">
          Authority: {result.pagerank.toFixed(3)}
        </span>
      </div>
    </article>
  );
}
