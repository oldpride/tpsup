#!/usr/bin/env python
import argparse
import os
import sys
import textwrap

from pywinauto import Desktop
import psutil


def get_process_details(pid: int):
    try:
        p = psutil.Process(pid)
        exe = p.exe() or ""
        args = " ".join(p.cmdline()) if p.cmdline() else ""
        return exe, args
    except Exception:
        return "", ""


def list_windows():
    desktop = Desktop(backend="win32")
    rows = []

    for w in desktop.windows():
        try:
            pid = int(w.process_id())
        except Exception:
            continue

        try:
            rect = w.rectangle()
            x = rect.left
            y = rect.top
            width = rect.width()
            height = rect.height()
        except Exception:
            x = y = width = height = None

        exe, args = get_process_details(pid)
        rows.append({
            "title": (w.window_text() or "").strip(),
            "class_name": w.class_name() or "",
            "pid": pid,
            "executable": exe,
            "args": args,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        })

    return rows


def print_rows(rows):
    rows = sorted(
        rows,
        key=lambda r: (
            r["class_name"],
            r["x"] if isinstance(r["x"], (int, float)) else 0,
            r["y"] if isinstance(r["y"], (int, float)) else 0,
        ),
    )

    if not rows:
        print("No windows found.")
        return

    class_width = max(10, max(len(r["class_name"]) for r in rows))
    pid_width = max(8, max(len(str(r["pid"])) for r in rows))
    exe_width = max(10, max(len(r["executable"]) for r in rows))
    x_width = max(8, max(len(str(r["x"])) if r["x"] is not None else 0 for r in rows))
    y_width = max(8, max(len(str(r["y"])) if r["y"] is not None else 0 for r in rows))
    w_width = max(8, max(len(str(r["width"])) if r["width"] is not None else 0 for r in rows))
    h_width = max(8, max(len(str(r["height"])) if r["height"] is not None else 0 for r in rows))
    title_width = max(10, max(len(r["title"]) for r in rows))
    args_width = max(10, max(len(r["args"]) for r in rows))

    header = (
        f"{'class_name':<{class_width}}  "
        f"{'pid':>{pid_width}}  "
        f"{'x':>{x_width}}  {'y':>{y_width}}  "
        f"{'width':>{w_width}}  {'height':>{h_width}}  "
        f"{'executable':<{exe_width}}  "
        f"{'title':<{title_width}}  "
        f"{'args':<{args_width}}"
    )
    print(header)
    print("-" * len(header))

    for r in rows:
        print(
            f"{r['class_name']:<{class_width}}  "
            f"{r['pid']:>{pid_width}}  "
            f"{str(r['x']) if r['x'] is not None else '':>{x_width}}  "
            f"{str(r['y']) if r['y'] is not None else '':>{y_width}}  "
            f"{str(r['width']) if r['width'] is not None else '':>{w_width}}  "
            f"{str(r['height']) if r['height'] is not None else '':>{h_width}}  "
            f"{r['executable']:<{exe_width}}  "
            f"{r['title']:<{title_width}}  "
            f"{r['args']:<{args_width}}"
        )


def main():
    prog = os.path.basename(sys.argv[0])
    usage = textwrap.dedent("""
        list all current windows with class_name, pid, executable, args, and x,y coordinates.
    """)

    examples = textwrap.dedent(f"""
        examples:
            {prog}
            {prog} --title
    """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )
    parser.add_argument(
        "--title",
        action="store_true",
        help="show the window title as a separate field (already included in default output)",
    )
    args = parser.parse_args()

    rows = list_windows()
    if args.title:
        # title is already included by default; this just keeps compatibility with the example.
        pass

    print_rows(rows)
    print(f"\nTotal windows: {len(rows)}")


if __name__ == "__main__":
    main()
