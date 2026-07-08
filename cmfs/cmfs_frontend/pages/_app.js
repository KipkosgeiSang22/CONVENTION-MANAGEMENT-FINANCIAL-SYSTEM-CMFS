import ErrorBoundary from '../components/ErrorBoundary';
import '../styles/globals.css';

export default function App({ Component, pageProps }) {
  return (
    <ErrorBoundary>
      <Component {...pageProps} />
    </ErrorBoundary>
  );
}