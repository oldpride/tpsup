#!/usr/bin/env python
import argparse
import os
import sys
import textwrap

from pywinauto import Desktop
import psutil

from tpsup.windowstools import is_window_winTypes, what_are_winTypes


def get_process_details(pid: int):
    try:
        p = psutil.Process(pid)
        exe = p.exe() or ""
        args = " ".join(p.cmdline()) if p.cmdline() else ""
        return exe, args
    except Exception:
        return "", ""


def list_windows(winTypes=None, title_pattern=None):
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

        try:
            visible = bool(w.is_visible())
        except Exception:
            visible = None
        if winTypes and not is_window_winTypes(w, winTypes):
            continue

        title = (w.window_text() or "").strip()
        if title_pattern:
            if not title:
                continue

            if title_pattern not in title:
                continue

        rows.append({
            "title": title,
            "class_name": w.class_name() or "",
            "pid": pid,
            "executable": exe,
            "args": args,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "visible": visible,
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
    visible_width = max(8, max(len(str(r["visible"])) if r["visible"] is not None else 0 for r in rows))
    title_width = max(10, max(len(r["title"]) for r in rows))
    args_width = max(10, max(len(r["args"]) for r in rows))

    header = (
        f"{'class_name':<{class_width}}  "
        f"{'pid':>{pid_width}}  "
        f"{'x':>{x_width}}  {'y':>{y_width}}  "
        f"{'width':>{w_width}}  {'height':>{h_width}}  "
        f"{'visible':>{visible_width}}  "
        f"{'title':<{title_width}}  "
        f"{'executable':<{exe_width}}  "
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
            f"{str(r['visible']) if r['visible'] is not None else '':>{visible_width}}  "
            f"{r['title']:<{title_width}}  "
            f"{r['executable']:<{exe_width}}  "
            f"{r['args']:<{args_width}}"
        )

def main():
    prog = os.path.basename(sys.argv[0])
    usage = textwrap.dedent(f"""
    usage:
        list all current windows with title,class_name, pid, executable, args, and x,y coordinates.
        {prog}
        {prog} -tp <title_pattern> -wt <winTypes>

{what_are_winTypes}
    
    """)

    examples = textwrap.dedent(f"""
    examples:
        {prog} | less -S
        {prog} -tp tian
        {prog} -wt putty,mintty
    """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )
    parser.add_argument(
        "-tp","--title_pattern",
        action="store",
        type=str,
        default=None,
        help="show only window matching the title pattern",
    )

    parser.add_argument(
        "-wt","--winTypes",
        action="store",
        type=str,
        default=None,
        help="show only window matching the winTypes, connected by commas, e.g., putty,mintty",
    )
    args = parser.parse_args()

    rows = list_windows(winTypes=args.winTypes, title_pattern=args.title_pattern)

    print_rows(rows)
    print(f"\nTotal windows: {len(rows)}")


if __name__ == "__main__":
    main()
