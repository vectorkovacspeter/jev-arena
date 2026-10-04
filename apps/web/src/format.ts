type N = number | null | undefined;
const DASH = "—";
/** Returns the tag if it is a valid BCP 47 tag, otherwise "en", so formatters never throw during render. */
export const safeLocale = (tag: string): string => {
  try {
    Intl.getCanonicalLocales(tag);
    return tag;
  } catch {
    return "en";
  }
};
const nf = (locale: string, o: Intl.NumberFormatOptions) => new Intl.NumberFormat(safeLocale(locale), o);

export const number = (locale: string, v: N, maxDigits = 0) =>
  v == null ? DASH : nf(locale, { maximumFractionDigits: maxDigits }).format(v);

export const fixed = (locale: string, v: N, digits: number) =>
  v == null ? DASH : nf(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: false }).format(v);

export const percent = (locale: string, v: N, digits = 1) =>
  v == null ? DASH : nf(locale, { style: "percent", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v);

/** Signed percentage-point delta without unit; callers append t("common.pp"). */
export const points = (locale: string, v: N, digits = 1) =>
  v == null ? DASH : nf(locale, { signDisplay: "exceptZero", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v * 100);

/** SI symbols (ms, s) are language-neutral; only the number is localized. */
export const duration = (locale: string, ms: N) => {
  if (ms == null) return DASH;
  if (ms < 1) return "<1 ms";
  if (ms >= 1000) return `${fixed(locale, ms / 1000, 2)} s`;
  return `${number(locale, ms, ms < 10 ? 1 : 0)} ms`;
};

export const shortDate = (locale: string, epochSeconds: number) =>
  new Date(epochSeconds * 1000).toLocaleDateString(safeLocale(locale), { month: "short", day: "numeric" });

/** Language name in the display language (e.g. "Hungarian" / "magyar"); falls back to the code. */
export const languageName = (locale: string, code: string) => {
  try {
    return new Intl.DisplayNames([safeLocale(locale)], { type: "language" }).of(code) ?? code;
  } catch {
    return code;
  }
};
