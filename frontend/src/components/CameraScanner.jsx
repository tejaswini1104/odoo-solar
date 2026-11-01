import React, { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import jsQR from 'jsqr';

// Reads barcodes and QR codes from the camera. It uses the browser's built-in detector when there is one, and reads QR codes
// with jsQR otherwise (for example Chrome on a laptop). Without camera permission a message shows and typing still works.
export default function CameraScanner({ onScan, onClose }) {
  const video = useRef(null);
  const [message, setMessage] = useState('Starting the camera...');
  // Keep the latest callback without restarting the camera every time the parent re-renders
  const latestOnScan = useRef(onScan);

  useEffect(() => {
    latestOnScan.current = onScan;
  }, [onScan]);

  useEffect(() => {
    let stream;
    let stopped = false;
    let timer;
    const detector = 'BarcodeDetector' in window ? new window.BarcodeDetector() : null;
    const canvas = document.createElement('canvas');

    const read = async () => {
      const el = video.current;
      if (detector) {
        const found = await detector.detect(el);
        return found.length > 0 ? found[0].rawValue : null;
      }
      if (!el.videoWidth) return null;
      canvas.width = el.videoWidth;
      canvas.height = el.videoHeight;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(el, 0, 0);
      const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const code = jsQR(image.data, image.width, image.height);
      return code ? code.data : null;
    };

    const tick = async () => {
      if (stopped || !video.current) return;
      try {
        const value = await read();
        if (value) {
          latestOnScan.current(value);
          // Pause briefly so one label is not read twice in a row
          timer = setTimeout(tick, 1500);
          return;
        }
      } catch {
        // A frame that cannot be read is skipped
      }
      timer = setTimeout(tick, 250);
    };

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then((s) => {
        if (stopped) { s.getTracks().forEach((t) => t.stop()); return; }
        stream = s;
        video.current.srcObject = s;
        video.current.play();
        setMessage('Point the camera at the QR code or barcode on the unit.');
        tick();
      })
      .catch(() => setMessage('The camera could not be opened. Allow camera access, or type the serial number instead.'));

    return () => {
      stopped = true;
      clearTimeout(timer);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div className="rounded-lg border border-slate-300 bg-slate-900 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-800 text-slate-200 text-[11px]">
        <span>{message}</span>
        <button type="button" onClick={onClose} aria-label="Close camera"><X className="w-4 h-4" /></button>
      </div>
      <video ref={video} muted playsInline className="w-full max-h-56 object-cover" />
    </div>
  );
}
