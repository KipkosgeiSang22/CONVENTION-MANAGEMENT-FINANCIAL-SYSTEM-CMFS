/**
 * FILE: cmfs/cmfs_frontend/components/gate/QrScanner.js
 * ACTION: CREATE (Phase 8)
 *
 * Continuous camera QR scanner using jsQR (pure-JS decode, no native
 * deps, works fully offline once the page/assets are cached by the
 * service worker). Decodes frames on a requestAnimationFrame loop and
 * calls onScan(text) whenever a code is found, with a short per-code
 * cooldown so holding a badge in front of the camera doesn't fire the
 * same scan a dozen times in a row.
 */
import { useEffect, useRef, useState } from 'react';
import jsQR from 'jsqr';

const SCAN_COOLDOWN_MS = 3000;

export default function QrScanner({ onScan, paused = false }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const rafRef = useRef(null);
  const lastScanRef = useRef({ text: null, at: 0 });
  const [cameraError, setCameraError] = useState('');
  const [ready, setReady] = useState(false);

  // "Latest ref" pattern: tick() below is set up once (empty-deps effect)
  // and recurses via requestAnimationFrame forever, so it can never see a
  // *new* onScan/paused value through a normal closure — only through a
  // ref kept fresh on every render.
  const onScanRef = useRef(onScan);
  const pausedRef = useRef(paused);
  useEffect(() => { onScanRef.current = onScan; });
  useEffect(() => { pausedRef.current = paused; });

  useEffect(() => {
    if (!canvasRef.current) canvasRef.current = document.createElement('canvas');
    let stream;
    let cancelled = false;

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
          audio: false,
        });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setReady(true);
          tick();
        }
      } catch (err) {
        setCameraError('Camera access denied or unavailable. Enable camera permission and reload.');
      }
    }

    function tick() {
      if (cancelled) return;
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && video.readyState === video.HAVE_ENOUGH_DATA && !pausedRef.current) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        if (code && code.data) {
          const now = Date.now();
          const last = lastScanRef.current;
          if (code.data !== last.text || now - last.at > SCAN_COOLDOWN_MS) {
            lastScanRef.current = { text: code.data, at: now };
            onScanRef.current(code.data);
          }
        }
      }
      rafRef.current = requestAnimationFrame(tick);
    }

    start();

    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (stream) stream.getTracks().forEach(t => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="relative bg-black rounded-xl overflow-hidden aspect-square max-w-sm mx-auto">
      <video ref={videoRef} playsInline muted className="w-full h-full object-cover" />
      {!ready && !cameraError && (
        <div className="absolute inset-0 flex items-center justify-center text-white text-sm">
          Starting camera…
        </div>
      )}
      {cameraError && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-80 text-white text-sm text-center px-6">
          {cameraError}
        </div>
      )}
      {ready && !paused && (
        <div className="absolute inset-8 border-4 border-white/70 rounded-2xl pointer-events-none" />
      )}
    </div>
  );
}
