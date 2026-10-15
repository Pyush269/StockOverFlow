import { useEffect, useState } from 'react';

export function useResource(loader, revision = 0) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    loader(controller.signal).then((data) => {
      if (current) setState({ data, loading: false, error: null });
    }).catch((error) => {
      if (current && error.name !== 'AbortError') setState((previous) => ({ ...previous, loading: false, error }));
    });
    return () => { current = false; controller.abort(); };
  }, [loader, revision]);
  return state;
}

export function useDebounced(value, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
