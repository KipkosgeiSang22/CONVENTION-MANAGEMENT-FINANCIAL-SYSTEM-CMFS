/**
 * FILE: cmfs/cmfs_frontend/pages/_document.js
 * ACTION: CREATE (Phase 8)
 *
 * Site-wide <head> tags needed for PWA installability (manifest link,
 * theme-color, apple touch icon). Service worker *registration* itself
 * lives in _app.js — this file only declares static <head> content.
 */
import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#2563eb" />
        <link rel="icon" href="/icons/icon-192.png" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="Gate Check-In" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
