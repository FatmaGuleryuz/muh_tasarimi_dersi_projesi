const tr = (n: number, digits: number) =>
  n.toLocaleString("tr-TR", { minimumFractionDigits: digits, maximumFractionDigits: digits });

/** 0.234 -> "%23,4" */
export const pct = (x: number, digits = 1) => `%${tr(x * 100, digits)}`;
/** 1409 -> "1.409" */
export const num = (n: number) => n.toLocaleString("tr-TR");
/** 0.8475 -> "0,847" */
export const dec = (x: number, digits = 3) => tr(x, digits);
