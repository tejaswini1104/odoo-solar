// What a scanner reads from a unit's label. The QR code holds the warranty check address with the serial number in it,
// while a plain barcode holds just the serial. Either way the serial number comes out.
export function serialFromScan(raw) {
  const text = raw ?? '';
  if (/^https?:\/\//i.test(text.trim())) {
    try {
      const serial = new URL(text.trim()).searchParams.get('serial');
      if (serial) return serial;
    } catch {
      // not a web address after all: use it as typed
    }
  }
  return text;
}
