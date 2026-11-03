import { useTheme } from '@/hooks/use-theme';
import { cardDocument } from '@/lib/card-document';

/**
 * Shows a card's HTML in the browser. react-native-webview does not support web, so this uses an
 * iframe. The `sandbox` attribute blocks forms, pop-ups and navigation of the app;
 * `allow-same-origin` is needed for images and audio from the backend to load (a fully sandboxed
 * page counts as coming from nowhere, and the browser then blocks loads from a local server), and
 * `allow-scripts` for KaTeX (math). Card content itself cannot run scripts: the backend sanitizes it
 * and the page's content security policy only allows KaTeX's files.
 */
export function CardHtml({ html }: { html: string }) {
  const colors = useTheme();
  return (
    <iframe
      title="card"
      sandbox="allow-same-origin allow-scripts"
      srcDoc={cardDocument(html, colors)}
      style={{ flex: 1, width: '100%', border: 'none', backgroundColor: colors.background }}
    />
  );
}
