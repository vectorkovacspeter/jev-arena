import tseslint from "typescript-eslint";
import i18next from "eslint-plugin-i18next";

export default [
  { files: ["apps/web/src/**/*.tsx", "apps/shared/**/*.tsx"],
    languageOptions: { parser: tseslint.parser },
    plugins: { i18next },
    rules: { "i18next/no-literal-string": ["error", { mode: "jsx-text-only",
      "jsx-attributes": { include: ["title", "aria-label", "placeholder", "alt"] },
      words: { exclude: ["Jev Arena", "Jev", "—", "·", "/", "%", "\\s*[→←×+]\\s*", "[0-9.,:]+", "F1", "MRR", "nDCG@10", "N/A"] } }] } },
];
