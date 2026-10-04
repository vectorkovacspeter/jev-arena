import type { TFunction } from "i18next";

export const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export const packLabel = (t: TFunction, name: string) => t(`packs.${slug(name)}`, { defaultValue: name });
export const familyLabel = (t: TFunction, name: string) => t(`families.${slug(name)}`, { defaultValue: name });
