/**
 * Axios HTTP client with request/response interceptors.
 *
 * - Request interceptor: adds default headers, logging
 * - Response interceptor: handles errors, transforms data
 */

import axios, {
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ===== Request Interceptor =====
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add timestamp to track request duration
    (config as any).__startTime = Date.now();

    // Log outgoing requests in development
    if (process.env.NODE_ENV === "development") {
      console.log(
        `[API] → ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`,
        config.params || ""
      );
    }

    return config;
  },
  (error: AxiosError) => {
    console.error("[API] Request error:", error.message);
    return Promise.reject(error);
  }
);

// ===== Response Interceptor =====
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Calculate request duration
    const startTime = (response.config as any).__startTime;
    const duration = startTime ? Date.now() - startTime : 0;

    // Log response in development
    if (process.env.NODE_ENV === "development") {
      console.log(
        `[API] ← ${response.status} ${response.config.url} (${duration}ms)`
      );
    }

    return response;
  },
  (error: AxiosError) => {
    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const url = error.config?.url || "unknown";

      switch (status) {
        case 400:
          console.error(`[API] Bad request: ${url}`);
          break;
        case 404:
          console.error(`[API] Not found: ${url}`);
          break;
        case 429:
          console.error(`[API] Rate limited: ${url}. Retrying...`);
          break;
        case 500:
        case 502:
        case 503:
          console.error(`[API] Server error (${status}): ${url}`);
          break;
        default:
          console.error(`[API] Error ${status}: ${url}`);
      }
    } else if (error.request) {
      // Network error — no response received
      console.error(
        "[API] Network error — is the backend running?",
        error.message
      );
    } else {
      console.error("[API] Request setup error:", error.message);
    }

    return Promise.reject(error);
  }
);

export default api;
