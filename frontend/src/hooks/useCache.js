import { useState, useEffect, useCallback, useRef } from 'react';

// Cache em memória com TTL
const cache = new Map();

const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutos

export const useCache = (key, fetcher, options = {}) => {
  const { ttl = DEFAULT_TTL, enabled = true } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const getCachedData = useCallback(() => {
    const cached = cache.get(key);
    if (cached && Date.now() < cached.expiry) {
      return cached.data;
    }
    cache.delete(key);
    return null;
  }, [key]);

  const setCachedData = useCallback((data) => {
    cache.set(key, {
      data,
      expiry: Date.now() + ttl
    });
  }, [key, ttl]);

  const fetchData = useCallback(async (force = false) => {
    if (!enabled) return;

    // Verificar cache primeiro
    if (!force) {
      const cached = getCachedData();
      if (cached) {
        setData(cached);
        setLoading(false);
        return cached;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const result = await fetcherRef.current();
      setData(result);
      setCachedData(result);
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [enabled, getCachedData, setCachedData]);

  // Buscar dados no mount
  useEffect(() => {
    if (enabled) {
      fetchData();
    }
  }, [key, enabled]);

  // Função para invalidar cache
  const invalidate = useCallback(() => {
    cache.delete(key);
  }, [key]);

  // Função para refresh forçado
  const refresh = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  return { data, loading, error, refresh, invalidate };
};

// Função para invalidar cache por padrão
export const invalidateCachePattern = (pattern) => {
  const regex = new RegExp(pattern);
  for (const key of cache.keys()) {
    if (regex.test(key)) {
      cache.delete(key);
    }
  }
};

// Função para limpar todo o cache
export const clearCache = () => {
  cache.clear();
};

// Hook para dados paginados com cache
export const usePaginatedData = (baseFetcher, options = {}) => {
  const { pageSize = 20, initialPage = 1 } = options;
  const [page, setPage] = useState(initialPage);
  const [allData, setAllData] = useState([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPage = useCallback(async (pageNum, reset = false) => {
    setLoading(true);
    setError(null);

    try {
      const result = await baseFetcher(pageNum, pageSize);
      const items = result.items || result.data || result;
      const total = result.total || items.length;

      setAllData(prev => reset ? items : [...prev, ...items]);
      setHasMore(allData.length + items.length < total);
      setPage(pageNum);
      
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [baseFetcher, pageSize, allData.length]);

  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      return fetchPage(page + 1);
    }
  }, [loading, hasMore, page, fetchPage]);

  const refresh = useCallback(() => {
    setAllData([]);
    setHasMore(true);
    return fetchPage(1, true);
  }, [fetchPage]);

  // Carregar primeira página
  useEffect(() => {
    fetchPage(1, true);
  }, []);

  return {
    data: allData,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
    page
  };
};

export default useCache;
