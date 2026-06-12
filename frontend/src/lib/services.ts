/**
 * API service layer — all Finder API calls go through here.
 */

import api from "./api";
import { SearchResponse, StatsResponse } from "@/types";

export const searchService = {
  /**
   * Search for web pages matching a query.
   */
  async search(
    query: string,
    page: number = 1,
    size: number = 10
  ): Promise<SearchResponse> {
    const response = await api.get<SearchResponse>("/api/search", {
      params: { q: query, page, size },
    });
    return response.data;
  },

  /**
   * Get system statistics (crawl counts, index size, etc.)
   */
  async getStats(): Promise<StatsResponse> {
    const response = await api.get<StatsResponse>("/api/stats");
    return response.data;
  },
};
