import { useEffect, useState } from 'react';
import { setCallbacks, logout } from '../lib/auth';

/**
 * Wrap your authenticated layout with this.
 * Shows a warning modal 2 minutes before inactivity logout.
 */
export default function InactivityGuard({ children }) {
  const [showWarning, setShowWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(120);
  let countdown = null;

  useEffect(() => {
    setCallbacks({
      onWarning: () => {
        setShowWarning(true);
        setSecondsLeft(120);
        countdown = setInterval(() => {
          setSecondsLeft(s => {
            if (s <= 1) { clearInterval(countdown); return 0; }
            return s - 1;
          });
        }, 1000);
      },
      onLogout: (reason) => {
        setShowWarning(false);
        clearInterval(countdown);
        window.location.href = '/auth/login?reason=' + reason;
      },
    });
    return () => clearInterval(countdown);
  }, []);

  function handleStayLoggedIn() {
    setShowWarning(false);
    clearInterval(countdown);
    // Reset inactivity by firing a synthetic interaction
    window.dispatchEvent(new MouseEvent('mousemove'));
  }

  async function handleLogoutNow() {
    setShowWarning(false);
    clearInterval(countdown);
    await logout();
  }

  return (
    <>
      {children}
      {showWarning && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-8 max-w-sm w-full text-center">
            <h2 className="text-xl font-bold text-gray-800 mb-2">Still there?</h2>
            <p className="text-gray-500 mb-4">
              You will be logged out in <strong className="text-red-600">{secondsLeft}s</strong> due to inactivity.
            </p>
            <div className="flex gap-3 justify-center">
              <button onClick={handleStayLoggedIn}
                className="bg-blue-600 text-white px-5 py-2 rounded font-medium hover:bg-blue-700">
                Stay Logged In
              </button>
              <button onClick={handleLogoutNow}
                className="bg-gray-100 text-gray-700 px-5 py-2 rounded font-medium hover:bg-gray-200">
                Log Out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}