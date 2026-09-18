"""Interactive setup helpers for CSES Kit."""
from __future__ import annotations

import getpass
import json
import os
import sys
import termios
import tty

from cses_lib import (
    env_credentials,
    login as do_login,
    repo_root,
    save_env_values,
    slugify_category,
)
from roadmap import load_problem_index


def arrow_menu(
    title: str,
    options: list[str],
    default: int = 0,
    interactive: bool | None = None,
) -> int:
    """Return an option index using arrow keys in a terminal."""
    if interactive is None:
        interactive = (
            sys.stdin.isatty()
            and sys.stdout.isatty()
            and not os.environ.get("CSES_TESTING")
        )
    if not interactive:
        raw = input(f"{title} [1-{len(options)}]: ").strip()
        try:
            selected = int(raw) - 1
        except ValueError:
            lowered = raw.lower()
            return next(
                (index for index, option in enumerate(options) if option.lower() == lowered),
                default,
            )
        return selected if 0 <= selected < len(options) else default

    selected = max(0, min(default, len(options) - 1))
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            print("\033[2J\033[H", end="")
            print(title)
            for index, option in enumerate(options):
                marker = ">" if index == selected else " "
                print(f" {marker} {option}")
            print("\nUse Up/Down and Enter. Home/End also work.", flush=True)
            key = sys.stdin.read(1)
            if key in ("\n", "\r"):
                return selected
            if key in ("k", "K"):
                selected = max(0, selected - 1)
            elif key in ("j", "J"):
                selected = min(len(options) - 1, selected + 1)
            elif key == "\x1b":
                sequence = sys.stdin.read(2)
                if sequence == "[A":
                    selected = max(0, selected - 1)
                elif sequence == "[B":
                    selected = min(len(options) - 1, selected + 1)
                elif sequence == "[H":
                    selected = 0
                elif sequence == "[F":
                    selected = len(options) - 1
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def choose_editor() -> str:
    choices = ["nvim", "vim", "code", "cursor", "custom"]
    option = choices[arrow_menu("Choose your editor", choices, default=2)]
    if option == "custom":
        custom = input("Custom editor command: ").strip()
        return custom or "code"
    return option


def _default_items() -> list[dict[str, object]]:
    path = os.path.join(repo_root(), "roadmaps", "default.json")
    try:
        index = load_problem_index(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    items = []
    for item in index.values():
        link = str(item.get("link") or "")
        if not link:
            continue
        category = str(item.get("category") or "misc")
        items.append({
            "name": str(item.get("name") or "Unknown"),
            "category": category,
            "category_slug": slugify_category(category),
            "link": link,
            "url": link,
        })
    return items


def _write_roadmap(items: list[dict[str, object]], filename: str) -> str:
    path = os.path.join(repo_root(), "problems", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2)
        fh.write("\n")
    return path


def _create_custom_roadmap(items: list[dict[str, object]]) -> str:
    selected = set(range(len(items)))
    if sys.stdin.isatty() and sys.stdout.isatty() and not os.environ.get("CSES_TESTING"):
        selected = set()
        index = 0
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                print("\033[2J\033[H", end="")
                print("Create your roadmap: Space selects, Enter saves, q cancels\n")
                start = max(0, min(index - 8, len(items) - 16))
                for row in range(start, min(len(items), start + 16)):
                    mark = "*" if row in selected else " "
                    cursor = ">" if row == index else " "
                    print(f"{cursor} [{mark}] {items[row].get('name', 'Unknown')}")
                print(f"\n{len(selected)} selected", flush=True)
                key = sys.stdin.read(1)
                if key in ("\n", "\r"):
                    break
                if key in ("q", "Q"):
                    return ""
                if key == " ":
                    if index in selected:
                        selected.remove(index)
                    else:
                        selected.add(index)
                elif key in ("j", "J"):
                    index = min(len(items) - 1, index + 1)
                elif key in ("k", "K"):
                    index = max(0, index - 1)
                elif key == "\x1b":
                    sequence = sys.stdin.read(2)
                    if sequence == "[A":
                        index = max(0, index - 1)
                    elif sequence == "[B":
                        index = min(len(items) - 1, index + 1)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    return _write_roadmap([items[i] for i in sorted(selected)], "my-roadmap.json")


def choose_roadmap() -> str:
    items = _default_items()
    default_path = os.path.join(repo_root(), "roadmaps", "default.json")
    categories = list(dict.fromkeys(str(item["category"]) for item in items))
    categories = categories or ["introductory", "sorting_and_searching"]
    choice = arrow_menu(
        "Choose your roadmap",
        ["CSES Category", "CSES Problem Set", "Import roadmap.json/.txt", "Create my own roadmap"],
    )
    if choice == 0:
        category = categories[arrow_menu("Choose a CSES category", categories)]
        category_items = [item for item in items if item["category"] == category]
        category_index = categories.index(category)
        return _write_roadmap(category_items, f"category-{category_index}.json")
    if choice == 1:
        return default_path
    if choice == 2:
        return input("Path to roadmap JSON/TXT: ").strip() or default_path
    return _create_custom_roadmap(items)


def cmd_setup(args) -> int:
    nick = args.nick or env_credentials()[0] or input("CSES username: ").strip()
    password = args.password or env_credentials()[1] or getpass.getpass("CSES password: ")
    if not nick or not password:
        print("error: username and password are required", file=sys.stderr)
        return 2

    editor = args.editor or os.environ.get("CSES_EDITOR") or choose_editor()
    repo_path = (
        args.repo_path
        or os.environ.get("CSES_PROBLEMS_DIR")
        or input("Existing problems directory [./problems]: ").strip()
        or os.path.join(repo_root(), "problems")
    )
    roadmap_path = args.roadmap or os.environ.get("CSES_ROADMAP") or choose_roadmap()
    values = {
        "CSES_NICK": nick,
        "CSES_PASS": password,
        "CSES_EDITOR": editor,
        "CSES_PROBLEMS_DIR": repo_path,
        "CSES_ROADMAP": roadmap_path,
    }
    if args.session_mode:
        values["CSES_SESSION_MODE"] = args.session_mode
    save_env_values(values)
    try:
        account = do_login(nick, password)
    except Exception as exc:  # noqa: BLE001
        print(f"setup saved, but login failed: {exc}", file=sys.stderr)
        return 1
    print("saved local CSES setup in .env")
    print(f"login successful: {account}")
    print("session mode:", values.get("CSES_SESSION_MODE", "cookie"))
    print("editor:", editor)
    print("problems path:", repo_path)
    return 0