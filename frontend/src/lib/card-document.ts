/**
 * Wraps a card's HTML in a complete page with styling, for display in a web view (phone) or an
 * iframe (browser). Scripts are disabled in both, so card content cannot run code.
 */
export function cardDocument(html: string, colors: { text: string; background: string }): string {
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body { margin: 0; background: ${colors.background}; color: ${colors.text}; }
  body {
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    font-size: 22px; line-height: 1.4; text-align: center;
    padding: 24px 16px; word-wrap: break-word;
  }
  hr#answer { border: none; border-top: 1px solid ${colors.text}33; margin: 20px 0; }
  img { max-width: 100%; height: auto; }
  /* The gap a Cloze card tests: [...] on the front, the answer on the back */
  .cloze { font-weight: bold; color: #208AEF; }
</style>
</head>
<body>${html}</body>
</html>`;
}
