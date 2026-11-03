import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

const subscribe = () => () => {};

/**
 * On web the page may be rendered on the server first, where the user's color scheme is unknown.
 * Report 'light' until the page is running in the browser, then the real scheme.
 */
export function useColorScheme() {
  const isBrowser = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  const colorScheme = useRNColorScheme();
  return isBrowser ? colorScheme : 'light';
}
