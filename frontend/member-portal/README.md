# Member Portal

Static, mobile-first bilingual (Swedish + Amharic) portal for church members.

## Architecture

- **No frameworks, no cookies, no tracking.** Plain HTML + CSS + vanilla JS.
- Content loaded from `content.json` at runtime.
- Language switcher toggles between Swedish and Amharic without page reload.
- Follows the same pattern as `frontend/wifi-intake-portal/`.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Entry point |
| `styles.css` | Mobile-first styles with Ge'ez script support |
| `app.js` | Pure functions + DOM renderer |
| `content.json` | Bilingual content (sv + am) |
| `tests/test_app.js` | Node assert tests for rendering logic |

## Fonts

Amharic (Ge'ez script) rendering requires Noto Sans Ethiopic. The CSS includes
a commented-out `@font-face` rule. To enable it:

1. Download `NotoSansEthiopic-Regular.woff2` from Google Fonts
2. Place it at `./fonts/NotoSansEthiopic-Regular.woff2`
3. Uncomment the `@font-face` block in `styles.css`

Until vendored, the browser will use system fallback fonts.

## Running tests

```bash
node tests/test_app.js
```

## Updating content

Edit `content.json` directly or use the Content Editor in admin-web (`/content-editor`).
