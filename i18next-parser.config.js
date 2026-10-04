// Keys used dynamically (`errors.${code}`, `packs.${slug}`, `status.${s}`, `nav.${id}` via pageKeys)
// can't be detected by the parser; these prefixes protect them. Add any new dynamic key family here.
// The parser tests patterns against "<namespace><namespaceSeparator><key>", so the default
// namespace "translation" and the ":" separator are part of the matched string.
const dynamic = ["errors", "readiness", "packs", "families", "status", "nav"];

export default {
  locales: ["en"],
  input: ["apps/web/src/**/*.{ts,tsx}", "apps/shared/**/*.tsx"],
  output: "locales/$LOCALE/ui.json",
  keySeparator: ".",
  namespaceSeparator: ":",
  keepRemoved: dynamic.map((prefix) => new RegExp(`^translation:${prefix}(\\.|$)`)),
  createOldCatalogs: false,
  failOnUpdate: false,
  sort: true,
  indentation: 2,
  defaultValue: (locale, ns, key, value) => value ?? "",
};
