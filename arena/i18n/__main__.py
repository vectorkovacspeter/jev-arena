import argparse
import sys
from arena.i18n import check

def _translate(args) -> int:
    from arena.i18n import engines, translated
    from arena.i18n.memory import TranslationMemory
    try:
        slot = translated.load_slots(args.lang).get(args.slot)
        if slot is None or slot.source != "translated": raise ValueError(f"{args.lang}: {args.slot} is not a translated slot")
        english = translated.english_cases(args.slot, slot)
        tm = TranslationMemory(args.lang, args.slot)
        texts = translated.texts_for(args.slot, english, slot)
        if args.dry_run:
            missing = tm.missing(texts)
            print(f"{args.lang}/{args.slot}: {len(texts)} unique texts, {len(missing)} to translate, {sum(len(t) for t in missing)} characters")
            print(engines.FREE_TIER_NOTE)
            return 0
        added = translated.translate(args.lang, args.slot, texts, args.engine or slot.engine or translated.DEFAULT_ENGINE, tm,
                                     lambda message: print(message, flush=True))
    except engines.ManualPending as e:
        print(e)
        return 0
    except (FileNotFoundError, ValueError, KeyError, RuntimeError, engines.Unavailable) as e:
        print(f"Error: {e}")
        return 1
    print(f"{args.lang}/{args.slot}: {added} new translations, {len(tm)} in memory ({tm.path})")
    return 0

def _review(args) -> int:
    import random
    from arena.i18n.memory import TranslationMemory
    tm = TranslationMemory(args.lang, args.slot)
    pending = [r for r in tm.rows() if not r["reviewed"] and not r.get("rejected")]
    sample = random.Random(args.seed).sample(pending, min(args.sample, len(pending)))
    reviewed = rejected = 0
    for i, row in enumerate(sample, 1):
        print(f"\n[{i}/{len(sample)}] en: {row['src']}\n{' ' * (len(str(i)) + len(str(len(sample))) + 3)}{args.lang}: {row['tgt']}")
        answer = ""
        while answer not in ("y", "n", "e", "q"): answer = input("Correct? y(es)/n(o)/e(dit)/q(uit): ").strip().lower()
        if answer == "q": break
        if answer == "y": tm.update(row["src"], reviewed=True); reviewed += 1
        elif answer == "e":
            edited = input("Corrected translation: ").strip()
            if edited: tm.update(row["src"], tgt=edited, reviewed=True); reviewed += 1
        else:  # n: offer an edit; an empty edit rejects the row (builds then treat it as missing)
            edited = input("Corrected translation (empty = reject): ").strip()
            if edited: tm.update(row["src"], tgt=edited, reviewed=True); reviewed += 1
            else: tm.update(row["src"], rejected=True); rejected += 1
    print(f"Reviewed {reviewed} of {len(sample)} sampled, rejected {rejected} ({len(pending) - reviewed - rejected} unreviewed left in {tm.path})")
    return 0

def _tm(args) -> int:
    from arena.i18n.memory import TranslationMemory
    tm = TranslationMemory(args.lang, args.slot)
    try:
        if args.action == "export": print(f"Exported {tm.export(args.file)} rows to {args.file}")
        else: print(f"Imported {tm.import_(args.file)} rows into {tm.path}")
    except (OSError, ValueError, KeyError) as e:
        print(f"Error: {e}")
        return 1
    return 0

def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m arena.i18n", description="Jev Arena translation tools")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="Validate locale catalogs against en")
    c.add_argument("--lang")
    c.add_argument("--quiet", action="store_true", help="Print errors only")
    n = sub.add_parser("new-language", help="Scaffold locales/<code>/ from en")
    n.add_argument("code"); n.add_argument("--name", required=True); n.add_argument("--native", required=True)
    p = sub.add_parser("prepare", help="Build a language's dataset packs into .arena/datasets/<lang>/")
    p.add_argument("--lang", required=True)
    p.add_argument("--only", choices=["native", "translated", "generated"])
    t = sub.add_parser("translate", help="Machine-translate a translated slot's missing texts into its translation memory")
    t.add_argument("--lang", required=True); t.add_argument("--slot", required=True)
    t.add_argument("--engine", help="manual, opus-mt, deepl or google (default: the slot's engine)")
    t.add_argument("--dry-run", action="store_true", help="Count texts and characters only")
    r = sub.add_parser("review", help="Review a sample of machine translations (y/n/e(dit)/q)")
    r.add_argument("--lang", required=True); r.add_argument("--slot", required=True)
    r.add_argument("--sample", type=int, default=20); r.add_argument("--seed", type=int, default=5090)
    m = sub.add_parser("tm", help="Export or import a translation memory (JSONL)")
    m.add_argument("action", choices=["export", "import"])
    m.add_argument("--lang", required=True); m.add_argument("--slot", required=True); m.add_argument("file")
    args = parser.parse_args(argv)
    if args.command in ("translate", "review", "tm"):
        return {"translate": _translate, "review": _review, "tm": _tm}[args.command](args)
    if args.command == "prepare":
        from arena.i18n import packs
        from arena.i18n.engines import EngineError
        try:
            result = packs.prepare_language(args.lang, lambda message: print(message, flush=True), only=args.only)
        except (FileNotFoundError, ValueError, KeyError, EngineError) as e:
            print(f"Error: {e}")
            return 1
        print(f"{args.lang}: {sum(result.values())} cases in {len(result)} pack files")
        return 0
    if args.command == "new-language":
        try:
            path = check.new_language(args.code, args.name, args.native)
            print(f"Created {path}. Next: translate ui.json (and prompts.yaml for test data), then run check.")
            return 0
        except (FileExistsError, ValueError) as e:
            print(f"Error: {e}")
            return 1
    issues = check.check(args.lang)
    for i in issues:
        if i.level == "error" or not args.quiet: print(f"{i.level.upper():7} {i.lang}/{i.file} {i.key}: {i.message}")
    for line in check.summary(args.lang): print(line)
    return 1 if any(i.level == "error" for i in issues) else 0

if __name__ == "__main__":
    sys.exit(main())
