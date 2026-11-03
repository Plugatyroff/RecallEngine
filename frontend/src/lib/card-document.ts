import { API_URL } from '@/services/api';

/** Where card media (images, audio) is served from; cards refer to files by name only. */
export const MEDIA_URL = `${API_URL}/api/v1/media/`;

/**
 * Wraps a card's HTML in a complete page with styling, for display in a web view (phone) or an
 * iframe (browser). Scripts are disabled in both, so card content cannot run code.
 *
 * The <base> element makes file names in the card, such as <img src="picture.jpg">, load from the
 * backend's media address, so cards never need to know where the backend runs.
 */
export function cardDocument(html: string, colors: { text: string; background: string }): string {
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="${MEDIA_URL}">
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
</style>
</head>
<body>${html}</body>
</html>`;
}
