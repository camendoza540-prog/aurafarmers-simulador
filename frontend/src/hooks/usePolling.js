import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api/client";

/**
 * Carga datos desde la API y, si `interval` > 0, los refresca periódicamente
 * mientras la pestaña está visible.
 */
export default function usePolling(url, interval = 0) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);

  const load = useCallback(async (silent = false) => {
    if (!url) return;
    if (!silent) setLoading(true);
    try {
      const res = await api.get(url);
      if (alive.current) {
        setData(res.data);
        setError(null);
      }
    } catch (e) {
      if (alive.current) setError(e);
    } finally {
      if (alive.current) setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    alive.current = true;
    load();
    let id;
    if (interval) {
      id = setInterval(() => {
        if (document.visibilityState === "visible") load(true);
      }, interval);
    }
    return () => {
      alive.current = false;
      if (id) clearInterval(id);
    };
  }, [load, interval]);

  return { data, error, loading, reload: load, setData };
}
