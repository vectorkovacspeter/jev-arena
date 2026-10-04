import i18next from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";
import { useMemo } from "react";
import * as f from "./format";
import type { LocaleInfo } from "./types";

// Bundled at build time so the standalone report works offline.
const modules = import.meta.glob("/locales/*/ui.json", { eager: true, import: "default" }) as Record<string, object>;
const metas = import.meta.glob("/locales/*/locale.json", { eager: true, import: "default" }) as Record<string, Omit<LocaleInfo, "completeness">>;
const code = (path: string) => path.split("/")[2];
const resources = Object.fromEntries(Object.entries(modules).map(([path, translation]) => [code(path), { translation }]));
export const bundledLocales: LocaleInfo[] = Object.values(metas)
  .map(m => ({ code: m.code, name: m.name, nativeName: m.nativeName, status: m.status, completeness: 1 }))
  .sort((a, b) => Number(a.code !== "en") - Number(b.code !== "en") || a.code.localeCompare(b.code));
export const i18n = i18next;

export async function initI18n(language: string) {
  await i18next.use(initReactI18next).init({
    resources, lng: language, fallbackLng: "en", returnEmptyString: false,
    interpolation: { escapeValue: false }, // React escapes.
  });
  document.documentElement.lang = language;
}

export async function setLanguage(code: string) {
  await i18next.changeLanguage(code);
  document.documentElement.lang = code;
}

export function useFormat() {
  const { i18n: active } = useTranslation();
  const l = active.language;
  return useMemo(() => ({
    number: (v: number | null | undefined, d = 0) => f.number(l, v, d),
    fixed: (v: number | null | undefined, d: number) => f.fixed(l, v, d),
    percent: (v: number | null | undefined, d = 1) => f.percent(l, v, d),
    points: (v: number | null | undefined, d = 1) => f.points(l, v, d),
    duration: (v: number | null | undefined) => f.duration(l, v),
    shortDate: (s: number) => f.shortDate(l, s),
  }), [l]);
}

export { useTranslation };
