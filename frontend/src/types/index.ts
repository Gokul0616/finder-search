/**
 * TypeScript types matching the FastAPI response schemas.
 */

export interface SearchResultItem {
  url: string;
  title: string;
  snippet: string;
  score: number;
  bm25_score: number;
  pagerank: number;
  domain: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  size: number;
  total_pages: number;
  results: SearchResultItem[];
  took_ms: number;
}

export interface StatsResponse {
  total_pages: number;
  crawled_pages: number;
  failed_pages: number;
  total_links: number;
  unique_domains: number;
  index_doc_count: number;
  index_size_mb: number;
}
