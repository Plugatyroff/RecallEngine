import { StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';

import { useTheme } from '@/hooks/use-theme';
import { cardDocument, MEDIA_URL } from '@/lib/card-document';

/** Shows a card's HTML on Android and iOS. The browser version is card-html.web.tsx. */
export function CardHtml({ html }: { html: string }) {
  const colors = useTheme();
  return (
    <WebView
      style={[styles.view, { backgroundColor: colors.background }]}
      originWhitelist={['*']}
      // baseUrl: file names in the card (images, audio) load from the backend's media address
      source={{ html: cardDocument(html, colors), baseUrl: MEDIA_URL }}
      javaScriptEnabled={false}
    />
  );
}

const styles = StyleSheet.create({
  view: { flex: 1 },
});
