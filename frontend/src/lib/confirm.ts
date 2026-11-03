import { Alert, Platform } from 'react-native';

/** Ask the user to confirm a destructive action. Resolves to true only if they confirm. */
export function confirm(title: string, message: string, confirmLabel: string): Promise<boolean> {
  if (Platform.OS === 'web') {
    // React Native's Alert has no buttons on web, so use the browser's dialog there
    return Promise.resolve(window.confirm(`${title}\n\n${message}`));
  }
  return new Promise((resolve) =>
    Alert.alert(
      title,
      message,
      [
        { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
        { text: confirmLabel, style: 'destructive', onPress: () => resolve(true) },
      ],
      { cancelable: true, onDismiss: () => resolve(false) },
    ),
  );
}

export type MenuOption = { label: string; destructive?: boolean };

/**
 * A small menu of actions, e.g. after a long press. Resolves to the chosen option's index, or
 * null if the menu was dismissed. On Android and iOS this is a native dialog with one button per
 * option; in the browser, where that is not available, each option is offered in turn.
 */
export function showMenu(title: string, options: MenuOption[]): Promise<number | null> {
  if (Platform.OS === 'web') {
    const index = options.findIndex((option) => window.confirm(`${title}\n\n${option.label}?`));
    return Promise.resolve(index === -1 ? null : index);
  }
  return new Promise((resolve) =>
    Alert.alert(
      title,
      undefined,
      [
        ...options.map((option, index) => ({
          text: option.label,
          style: option.destructive ? ('destructive' as const) : ('default' as const),
          onPress: () => resolve(index),
        })),
        { text: 'Cancel', style: 'cancel' as const, onPress: () => resolve(null) },
      ],
      { cancelable: true, onDismiss: () => resolve(null) },
    ),
  );
}
