import { StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';

import { useTheme } from '@/hooks/use-theme';
import { cardDocument } from '@/lib/card-document';

/** Shows a card's HTML on Android and iOS. The browser version is card-html.web.tsx. */
export function CardHtml({ html }: { html: string }) {
  const colors = useTheme();
  return (
    <WebView
      style={[styles.view, { backgroundColor: colors.background }]}
      originWhitelist={['*']}
      source={{ html: cardDocument(html, colors) }}
      javaScriptEnabled={false}
    />
  );
}

const styles = StyleSheet.create({
  view: { flex: 1 },
});
