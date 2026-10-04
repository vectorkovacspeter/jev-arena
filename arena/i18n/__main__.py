import argparse
import sys
from arena.i18n import check

def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m arena.i18n", description="Jev Arena translation tools")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="Validate locale catalogs against en")
    c.add_argument("--lang")
    c.add_argument("--quiet", action="store_true", help="Print errors only")
    n = sub.add_parser("new-language", help="Scaffold locales/<code>/ from en")
    n.add_argument("code"); n.add_argument("--name", required=True); n.add_argument("--native", required=True)
    args = parser.parse_args(argv)
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
