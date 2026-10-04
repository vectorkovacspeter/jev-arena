import type { ReactNode } from "react";
import { useTranslation } from "./i18n";

export function EnglishOnly({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  return <div lang="en">{i18n.language !== "en" && <p className="small muted english-only">{t("shell.englishOnly")}</p>}{children}</div>;
}
