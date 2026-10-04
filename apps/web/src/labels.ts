import type { TFunction } from "i18next";

export const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export const packLabel = (t: TFunction, name: string) => t(`packs.${slug(name)}`, { defaultValue: name });
export const familyLabel = (t: TFunction, name: string) => t(`families.${slug(name)}`, { defaultValue: name });

/** Display text for a failure: coded API errors use `errors.<code>`, client-side failures carry their own catalog `key`. */
export const errorText = (t: TFunction, e: unknown) => {
  const x = e as Error & { code?: string; key?: string; params?: Record<string, unknown> };
  if (x.key) return t(x.key, { ...x.params, defaultValue: x.message });
  if (!x.code) return x.message;
  const params = { ...x.params };
  if (x.code === "setup_needed" && Array.isArray(params.models))
    params.details = (params.models as { name: string; reason_code: string }[])
      .map((m) => `${m.name}: ${t(`readiness.${m.reason_code}`)}`)
      .join("; ");
  return t(`errors.${x.code}`, { ...params, defaultValue: x.message });
};

/** Run language from the manifest; runs recorded before i18n have none and are English. */
export const runLanguage = (run: { manifest?: { language?: unknown } } | null | undefined) =>
  typeof run?.manifest?.language === "string" && run.manifest.language ? run.manifest.language : "en";

/** Test-data language to show: a saved report uses its run's language, a live workspace its current setting. */
export const dataLanguageFor = (
  offline: boolean,
  run: { manifest?: { language?: unknown } } | null | undefined,
  settingLanguage: string | null | undefined,
) => (offline ? runLanguage(run) : settingLanguage || "en");

/** Stable (English) id of an episode answer: non-English runs store the localized label in `answer` and the id in `answer_id`. */
export const answerId = (step: { answer: string | null; answer_id?: string | null } | null | undefined) =>
  step ? (step.answer_id ?? step.answer) : null;

/** Slots that Prepare can still fill: not ready, not missing, and part of a fixed-size suite. */
export const unpreparedSlots = <S extends { source: string; ready: boolean; expected: number | null }>(slots: S[] | undefined) =>
  (slots || []).filter((s) => !s.ready && s.source !== "missing" && s.expected != null);
