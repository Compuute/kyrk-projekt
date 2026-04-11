# wifi-intake-portal

Static, privacy-first Wi-Fi landing portal. No frameworks. No cookies. No
tracking.

## Stack

- Plain HTML + CSS
- Tiny vanilla JS (`content.js`) that picks sections from a JSON content config
- Content config is fetched from a Cloud Storage bucket, pushed by an n8n
  workflow (see `automation/n8n/workflows/wifi_portal_content_update.json`)

## Why not React?

This page is a static landing, not an app. Plain HTML is faster, simpler,
cheaper to host, and easier to audit. n8n pushes updated content — no
build pipeline required.

## Files

```
wifi-intake-portal/
├── index.html
├── styles.css
├── content.js                 # content decision logic (tested)
├── content-config.example.json # example content config
├── tests/
│   └── test_content_decision.js
└── README.md
```

## Running locally

Open `index.html` in any browser. To test with a custom config:

```bash
python3 -m http.server 8000
# open http://localhost:8000/
```

## Testing

```bash
node tests/test_content_decision.js
```

Zero dependencies — the test file uses Node's built-in `assert` module.

## n8n integration

The n8n workflow `wifi_portal_content_update` generates a `content.json`
file (GREEN zone only) and uploads it to
`gs://<project>-wifi-portal-content/content.json`. The portal fetches this
file at load time.

## Privacy

- No cookies.
- No analytics.
- No third-party scripts.
- No auto-identification.
- Every asset is local.
- Content is GREEN zone only — no RED data ever touches this module.
