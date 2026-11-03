// Renders the math on a card page with KaTeX. Loaded by the app's card view after KaTeX itself.
// Delimiters are the ones Anki uses: \( ... \) inline and \[ ... \] on its own line, plus $$ ... $$.
document.addEventListener('DOMContentLoaded', function () {
  renderMathInElement(document.body, {
    delimiters: [
      { left: '\\(', right: '\\)', display: false },
      { left: '\\[', right: '\\]', display: true },
      { left: '$$', right: '$$', display: true },
    ],
    // Show broken formulas as their source in red instead of failing the whole card
    throwOnError: false,
  });
});
