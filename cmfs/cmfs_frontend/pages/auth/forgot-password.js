import { useState } from 'react';
import { api } from '../../lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/api/auth/password-reset/request/', { email });
      setSubmitted(true);
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (submitted) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md text-center">
        <h2 className="text-xl font-bold text-gray-800 mb-2">Check your email</h2>
        <p className="text-gray-500 mb-6">If that email is registered, a reset link has been sent. It expires in 1 hour.</p>
        <a href="/auth/login" className="text-blue-600 hover:underline text-sm">← Back to login</a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Forgot Password</h1>
        <p className="text-gray-500 mb-6">Enter your email address and we will send you a reset link.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="email" required placeholder="your@email.com" value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
            {loading ? 'Sending…' : 'Send Reset Link'}
          </button>
          <p className="text-center text-sm">
            <a href="/auth/login" className="text-blue-600 hover:underline">← Back to login</a>
          </p>
        </form>
      </div>
    </div>
  );
}