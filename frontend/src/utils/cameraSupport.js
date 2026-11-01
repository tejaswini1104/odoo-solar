// True when this browser can read barcodes from the camera. Otherwise the keyboard or a handheld scanner is used.
export const cameraScanSupported = () =>
  typeof window !== 'undefined' && 'BarcodeDetector' in window && !!navigator.mediaDevices?.getUserMedia;
