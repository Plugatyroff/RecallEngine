# Static files

Served by the backend at `/static/…` and loaded by the app's card view.

- `katex/` — [KaTeX](https://katex.org) 0.18.11 (MIT, see `katex/LICENSE`) for rendering LaTeX math:
  `katex.min.js`, `katex.min.css`, `contrib/auto-render.min.js` and the `.woff2` fonts, copied from
  the npm package's `dist` folder. `render-math.js` is ours: it renders `\( \)`, `\[ \]` and `$$ $$`.
