import { useTheme } from '@/hooks/use-theme';
import { cardDocument } from '@/lib/card-document';

/**
 * Shows a card's HTML in the browser. react-native-webview does not support web, so this uses an
 * iframe. The `sandbox` attribute blocks scripts and other active content; `allow-same-origin` is
 * needed for images and audio from the backend to load (a fully sandboxed page counts as coming
 * from nowhere, and the browser then blocks it from loading files from a local server). Scripts
 * stay blocked because `allow-scripts` is not given.
 */
export function CardHtml({ html }: { html: string }) {
  const colors = useTheme();
  return (
    <iframe
      title="card"
      sandbox="allow-same-origin"
      srcDoc={cardDocument(html, colors)}
      style={{ flex: 1, width: '100%', border: 'none', backgroundColor: colors.background }}
    />
  );
}
