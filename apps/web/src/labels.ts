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
