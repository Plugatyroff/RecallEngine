import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';

import { ApiError } from '@/services/api';

type State<T> = { data: T | null; error: string | null; loading: boolean };

/**
 * Load data from the API whenever the screen comes into view, so lists are fresh after returning
 * from another screen (e.g. after adding a card).
 *
 * `load` must be stable between renders: pass a module-level function such as `api.topics`, or
 * wrap it in useCallback with the values it depends on. Otherwise it would reload on every render.
 */
export function useApi<T>(load: () => Promise<T>) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: true });

  const reload = useCallback(() => {
    let cancelled = false;
    load()
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch(
        (error: unknown) =>
          !cancelled &&
          setState((previous) => ({
            ...previous,
            error: error instanceof ApiError ? error.message : String(error),
            loading: false,
          })),
      );
    return () => {
      cancelled = true;
    };
  }, [load]);

  useFocusEffect(reload);

  return { ...state, reload };
}
