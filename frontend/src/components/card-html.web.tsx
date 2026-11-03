import { useTheme } from '@/hooks/use-theme';
import { cardDocument } from '@/lib/card-document';

/**
 * Shows a card's HTML in the browser. react-native-webview does not support web, so this uses an
 * iframe; the empty `sandbox` attribute blocks scripts and other active content.
 */
export function CardHtml({ html }: { html: string }) {
  const colors = useTheme();
  return (
    <iframe
      title="card"
      sandbox=""
      srcDoc={cardDocument(html, colors)}
      style={{ flex: 1, width: '100%', border: 'none', backgroundColor: colors.background }}
    />
  );
}
