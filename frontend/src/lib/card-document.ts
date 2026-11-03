import { API_URL } from '@/services/api';

/** Where card media (images, audio) is served from; cards refer to files by name only. */
export const MEDIA_URL = `${API_URL}/api/v1/media/`;
/** KaTeX, served by the backend, renders the LaTeX math in cards. */
const KATEX_URL = `${API_URL}/static/katex/`;

/**
 * Only allow what a card needs, as a second line of defence after the backend's sanitizer:
 * scripts only from the backend's KaTeX folder (so no inline scripts or onclick handlers), and
 * images, audio and fonts only from the backend (or images embedded as data: URLs).
 */
const CONTENT_SECURITY_POLICY = [
  "default-src 'none'",
  `script-src ${KATEX_URL}`,
  `style-src ${KATEX_URL} 'unsafe-inline'`,
  `font-src ${KATEX_URL}`,
  `img-src ${API_URL} data:`,
  `media-src ${API_URL}`,
].join('; ');

/**
 * Wraps a card's HTML in a complete page with styling, for display in a web view (phone) or an
 * iframe (browser).
 *
 * The <base> element makes file names in the card, such as <img src="picture.jpg">, load from the
 * backend's media address, so cards never need to know where the backend runs. KaTeX then turns
 * \( ... \) and \[ ... \] into typeset math.
 */
export function cardDocument(html: string, colors: { text: string; background: string }): string {
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="${CONTENT_SECURITY_POLICY}">
<base href="${MEDIA_URL}">
<link rel="stylesheet" href="${KATEX_URL}katex.min.css">
<script defer src="${KATEX_URL}katex.min.js"></script>
<script defer src="${KATEX_URL}contrib/auto-render.min.js"></script>
<script defer src="${KATEX_URL}render-math.js"></script>
<style>
  html, body { margin: 0; background: ${colors.background}; color: ${colors.text}; }
  body {
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    font-size: 22px; line-height: 1.4; text-align: center;
    padding: 24px 16px; word-wrap: break-word;
  }
  hr#answer { border: none; border-top: 1px solid ${colors.text}33; margin: 20px 0; }
  img { max-width: 100%; height: auto; }
  audio { display: block; width: 100%; max-width: 360px; margin: 12px auto; }
  /* The gap a Cloze card tests: [...] on the front, the answer on the back */
  .cloze { font-weight: bold; color: #208AEF; }
  /* Long formulas scroll sideways instead of overflowing the card */
  .katex-display { overflow-x: auto; overflow-y: hidden; }
</style>
</head>
<body>${html}</body>
</html>`;
}
