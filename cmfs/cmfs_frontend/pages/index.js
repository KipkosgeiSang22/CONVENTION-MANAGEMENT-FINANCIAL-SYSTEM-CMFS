/**
 * FILE: cmfs/cmfs_frontend/pages/index.js
 * ACTION: REPLACE
 *
 * The previous version of this file was an accidental duplicate of
 * pages/dashboard.js — visiting the root domain redirected everyone
 * straight to /auth/login, with no path to public registration. This
 * replaces it with an actual public landing page.
 */

import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="flex justify-between items-center px-6 py-4">
        <span className="text-lg font-bold text-gray-900">KSCF CMFS</span>
        <Link href="/auth/login" className="text-sm text-gray-500 hover:text-gray-700">
          Staff Login →
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">
            KSCF Convention Management &amp; Financial System
          </h1>
          <p className="text-gray-500 mb-8">
            Register a delegate for the upcoming convention and pay the registration
            fee securely via M-Pesa.
          </p>
          <Link
            href="/register"
            className="inline-block bg-blue-600 text-white rounded-lg px-8 py-3 font-medium hover:bg-blue-700 transition"
          >
            Register for Convention →
          </Link>
        </div>
      </main>

      <footer className="text-center text-xs text-gray-400 py-4">
        Kenya Students Christian Fellowship
      </footer>
    </div>
  );
}