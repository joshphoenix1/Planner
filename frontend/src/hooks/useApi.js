import { useState, useEffect, useCallback, useRef } from 'react';

export function useApi(fetcher, options = {}) {
  // Handle both old array format and new options object
  const deps = Array.isArray(options) ? options : [];
  const { refreshInterval } = Array.isArray(options) ? {} : options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    refetch();

    if (refreshInterval) {
      intervalRef.current = setInterval(refetch, refreshInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [refetch, refreshInterval]);

  return { data, loading, error, refetch, setData };
}
