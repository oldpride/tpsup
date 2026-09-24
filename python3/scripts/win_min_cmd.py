#!/usr/bin/env python
import argparse
import sys

from pywinauto import Desktop


def normalize_class_name(value):
    return (value or "").strip().lower()


def minimize_all_except_classes(class_names, verbose=False, dry_run=False):
    keep_classes = {normalize_class_name(name) for name in class_names}
    desktop = Desktop(backend="win32")
    minimized = []
    kept = []

    for w in desktop.windows():
        cls = normalize_class_name(w.class_name())
        title = (w.window_text() or "").strip()

        if cls in keep_classes:
            kept.append((cls, title or "<no title>"))
            if verbose:
                print(f"keep: {cls} | {title or '<no title>'}")
            continue

        try:
            if verbose:
                print(f"minimizing: {cls} | {title or '<no title>'} [{w.process_id()}]")

            if not dry_run:
                w.minimize()

            minimized.append((cls, title or cls))
        except Exception as e:
            print(f"failed to minimize {cls} | {title or '<no title>'}: {e}", file=sys.stderr)

    return minimized, kept


def restore_minimized_windows(class_names, verbose=False, dry_run=False):
    keep_classes = {normalize_class_name(name) for name in class_names}
    desktop = Desktop(backend="win32")
    restored = []

    for w in desktop.windows():
        cls = normalize_class_name(w.class_name())
        title = (w.window_text() or "").strip()

        if cls in keep_classes:
            continue

        try:
            if w.is_minimized():
                if verbose:
                    print(f"restoring: {cls} | {title or '<no title>'} [{w.process_id()}]")

                if not dry_run:
                    w.restore()
                restored.append((cls, title or cls))
        except Exception as e:
            print(f"failed to restore {cls} | {title or '<no title>'}: {e}", file=sys.stderr)

    return restored


def main():
    parser = argparse.ArgumentParser(
        description="Minimize all windows except those whose class names are listed."
    )
    parser.add_argument(
        "class_names",
        nargs="*",
        help="Window class names to keep visible, for example: putty mintty",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each window that is minimized or restored",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be minimized or restored without changing windows",
    )
    parser.add_argument(
        "-restore",
        action="store_true",
        help="Restore minimized windows to normal size instead of minimizing others",
    )
    args = parser.parse_args()

    if args.restore:
        restored = restore_minimized_windows(
            class_names=args.class_names,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )

        print(f"restored: {len(restored)}")
        if args.verbose:
            for cls, title in restored:
                print(f"  - {cls}: {title}")
        return

    minimized, kept = minimize_all_except_classes(
        class_names=args.class_names,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    print(f"minimized: {len(minimized)}")
    print(f"kept: {len(kept)}")

    if args.verbose:
        for cls, title in minimized:
            print(f"  - {cls}: {title}")
        for cls, title in kept:
            print(f"  + {cls}: {title}")


if __name__ == "__main__":
    main()
