import { useEffect } from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import '../styles/globals.css';

export default function App({ Component, pageProps }) {
  // Phase 8: registers /sw.js so the Gate Check-In page's app shell is
  // cached and can load with no connection. Safe to call unconditionally —
  // it's a no-op on browsers without Service Worker support, and only
  // ever runs client-side.
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        // Non-fatal: the app still works without offline caching, it just
        // won't survive a hard reload while offline.
      });
    }
  }, []);

  return (
    <ErrorBoundary>
      <Component {...pageProps} />
    </ErrorBoundary>
  );
}