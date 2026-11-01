// True when this browser can open the camera. The built-in barcode detector is used where there is one, and a small
// QR reader (jsQR) everywhere else, so a laptop webcam works too. Otherwise the keyboard or a handheld scanner is used.
export const cameraScanSupported = () =>
  typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;
