import { Languages } from "lucide-react";
import { useTranslation } from "./i18n";
import type { LocaleInfo } from "./types";

export function LanguageSwitcher({ locales, language, onChange }: { locales: LocaleInfo[]; language: string; onChange: (code: string) => void }) {
  const { t } = useTranslation();
  if (locales.length < 2) return null;
  return <label className="language-switcher" title={t("shell.language")}>
    <Languages size={16} aria-hidden="true" />
    <select aria-label={t("shell.language")} value={language} onChange={e => onChange(e.target.value)}>
      {locales.map(l => <option key={l.code} value={l.code}>{l.nativeName}{l.status === "beta" ? ` (${t("shell.beta")})` : ""}</option>)}
    </select>
  </label>;
}
