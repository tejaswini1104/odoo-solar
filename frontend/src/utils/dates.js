const pad = (n) => String(n).padStart(2, '0');

// The date in the browser's own time zone, as YYYY-MM-DD. (toISOString would give the UTC date, which in India
// is still yesterday until 5:30 in the morning.)
export const localIsoDate = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export const monthStartIso = (d = new Date()) => localIsoDate(new Date(d.getFullYear(), d.getMonth(), 1));
