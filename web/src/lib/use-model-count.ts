import { useEffect, useState } from "react";
import { getModelCount, getProviderCount } from "./api";

// Count fetchers keyed by a stable string so the module cache is shared per
// metric across every caller (Header search, Footer, etc.) in a browser
// session. Each is the single source of truth for that "count" on the client.
const fetchFns: Record<string, () => Promise<number>> = {
  models: getModelCount,
  providers: getProviderCount,
};

// Module-level caches: { metricKey -> { count | null, inflight } }
const caches: Record<
  string,
  { cached: number | null; inflight: Promise<number> | null }
> = {};

function loadCount(key: string): Promise<number> {
  const cache = (caches[key] ??= { cached: null, inflight: null });
  if (cache.cached !== null) return Promise.resolve(cache.cached);
  if (!cache.inflight) {
    cache.inflight = fetchFns[key]()
      .then((n) => {
        cache.inflight = null;
        // Only cache a usable (positive) count. If the API returned 0 / junk,
        // don't cache it so a later call retries and callers keep their
        // fallback rather than flashing 0.
        if (typeof n === "number" && n > 0) cache.cached = n;
        return n;
      })
      .catch((err) => {
        cache.inflight = null;
        throw err;
      });
  }
  return cache.inflight;
}

function useCount(key: string, fallback = 0): number {
  const cache = (caches[key] ??= { cached: null, inflight: null });
  const [count, setCount] = useState<number>(() =>
    cache.cached !== null ? cache.cached : fallback
  );

  useEffect(() => {
    let active = true;
    loadCount(key)
      .then((n) => {
        // Never override a good fallback with 0 / junk: keep the fallback so
        // nothing flashes 0.
        if (!active || typeof n !== "number" || n <= 0) return;
        setCount(n);
      })
      .catch(() => {
        /* keep fallback */
      });
    return () => {
      active = false;
    };
  }, [key]);

  return count;
}

/**
 * Live model count, cached at module scope. Falls back to `fallback` while
 * loading / on error so the UI never flashes 0.
 */
export function useModelCount(fallback = 0): number {
  return useCount("models", fallback);
}

/**
 * Live provider count (all registered providers), cached at module scope.
 * Falls back to `fallback` while loading / on error so the UI never flashes 0.
 */
export function useProviderCount(fallback = 0): number {
  return useCount("providers", fallback);
}