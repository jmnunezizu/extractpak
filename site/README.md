# SCUMMKit Site

Vite, React, and TypeScript landing page for future GitHub Pages publishing.

```bash
npm install
npm run dev
npm run build
```

The Vite base path is `/scummkit/` for GitHub Pages under
`jmnunezizu.github.io/scummkit/`.

## Analytics

Google Analytics is disabled unless a measurement ID is provided at build time:

```bash
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX npm run build
```

The GitHub Pages workflow reads the optional `GA_MEASUREMENT_ID` repository
secret and exposes it to Vite as `VITE_GA_MEASUREMENT_ID`.
