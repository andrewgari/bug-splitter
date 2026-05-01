#!/usr/bin/env python3
"""
patch_shops.py — Add TM51 (Bug Splitter) to Pokemart inventories.

Searches for shop inventory data across pokeemerald's source tree and adds
ITEM_TM51 to:
  - Lilycove City Department Store (all floors that sell TMs, if found)
  - All other mart inventory arrays that already sell TMs (optional broadening)

pokeemerald stores shop inventories in one of several places depending on
the repo version:
  - src/data/shops.h  (newer versions)
  - data/scripts/     (map-embedded scripts, usually .inc files)
  - src/data/map_data or map event C files

This script tries all known patterns and falls back to a broad search.

Usage:
  python3 patch_shops.py <pokeemerald_dir>
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"  Updated: {path}")


def abort(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Strategy 1 — src/data/shops.h  (modern pokeemerald layout)
# ---------------------------------------------------------------------------

SHOPS_H_CANDIDATES = [
    Path("src") / "data" / "shops.h",
    Path("src") / "data" / "pokemon" / "shops.h",
    Path("include") / "data" / "shops.h",
]


def _find_shops_h(poke_dir: Path) -> Path:
    for rel in SHOPS_H_CANDIDATES:
        p = poke_dir / rel
        if p.exists() and ("ITEM_TM" in read(p) or "PokemartItem" in read(p)):
            return p
    return None


def _add_to_array(content: str, array_name_hint: str, item_to_add: str) -> tuple[str, bool]:
    """
    Find a C array that looks like a shop inventory and add item_to_add to it.
    Returns (new_content, changed).

    The function looks for an array like:
        static const u16 sFoo[] = {
            ITEM_X,
            ITEM_Y,
            ITEM_NONE,   <- sentinel
        };
    and inserts item_to_add before the sentinel.
    """
    # Sentinel patterns used in pokeemerald for shop end-of-list
    sentinel_pat = r"ITEM_NONE|0x0000|ITEMS_END"

    # Find the array by hint in its name or nearby string
    array_start = content.find(array_name_hint)
    if array_start == -1:
        return content, False

    # Find the opening { after array_start
    brace_open = content.find("{", array_start)
    if brace_open == -1:
        return content, False

    # Find the closing };
    brace_close = content.find("};", brace_open)
    if brace_close == -1:
        return content, False

    body = content[brace_open:brace_close + 2]

    if item_to_add in body:
        return content, False  # Already present

    # Insert before the sentinel
    m_sentinel = re.search(sentinel_pat, body)
    if m_sentinel:
        insert_pos = brace_open + m_sentinel.start()
        new_content = content[:insert_pos] + f"{item_to_add},\n    " + content[insert_pos:]
        return new_content, True

    # No sentinel found — insert before closing brace
    insert_pos = brace_close
    new_content = content[:insert_pos] + f"    {item_to_add},\n" + content[insert_pos:]
    return new_content, True


def patch_shops_h(poke_dir: Path) -> bool:
    shops_h = _find_shops_h(poke_dir)
    if shops_h is None:
        return False

    content = read(shops_h)
    if "ITEM_TM51" in content:
        print(f"  Already patched: {shops_h}")
        return True

    # Find Lilycove / department store arrays — try several name patterns
    department_hints = [
        "LilycoveCity_DepartmentStore",
        "lilycove",
        "Lilycove",
        "DeptStore",
        "department",
        "Department",
    ]

    # Also add to any TM-selling array
    tm_arrays_updated = 0
    tm_array_names = re.findall(
        r"(s\w+(?:Item|Mart|Shop|Store|TM)\w*)\s*\[\s*\]\s*=\s*\{[^}]*ITEM_TM",
        content,
        re.IGNORECASE,
    )

    for arr_name in tm_array_names:
        content, changed = _add_to_array(content, arr_name, "ITEM_TM51")
        if changed:
            tm_arrays_updated += 1

    # Explicitly try department store
    dept_added = False
    for hint in department_hints:
        content, changed = _add_to_array(content, hint, "ITEM_TM51")
        if changed:
            dept_added = True
            print(f"  Added ITEM_TM51 to shop array containing '{hint}'")
            break

    if not dept_added and tm_arrays_updated == 0:
        # Last resort: add to the FIRST array that sells any TM
        m = re.search(
            r"(s\w+)\s*\[\s*\]\s*=\s*\{([^}]*ITEM_TM[^}]*)\}",
            content,
            re.DOTALL,
        )
        if m:
            content, changed = _add_to_array(content, m.group(1), "ITEM_TM51")
            if changed:
                print(f"  Added ITEM_TM51 to first TM-selling array: {m.group(1)}")
                tm_arrays_updated += 1

    if dept_added or tm_arrays_updated > 0:
        write(shops_h, content)
        return True

    return False


# ---------------------------------------------------------------------------
# Strategy 2 — Map script .inc files (data/scripts/ tree)
# ---------------------------------------------------------------------------

# In older pokeemerald the map scripts are in .inc files with pokemart commands
# Format:
#   LilycoveCity_DepartmentStore_2F_EventScript_Clerk1Mart:
#       pokemart LilycoveCity_DepartmentStore_2F_Clerk1Items
#   LilycoveCity_DepartmentStore_2F_Clerk1Items:
#       .2byte ITEM_TM_SOMETHING
#       ...
#       .2byte ITEM_NONE


def patch_map_scripts(poke_dir: Path) -> bool:
    """
    Search .inc and .s map script files for shop inventory lists and add TM51.
    Returns True if at least one file was patched.
    """
    script_dirs = [
        poke_dir / "data" / "scripts",
        poke_dir / "data" / "maps",
        poke_dir / "src" / "data" / "maps",
    ]

    patched_any = False
    for script_dir in script_dirs:
        if not script_dir.exists():
            continue
        # Search recursively for .inc and .s files
        for script_file in sorted(script_dir.rglob("*.inc")) + sorted(
            script_dir.rglob("*.s")
        ):
            content = read(script_file)
            if "ITEM_TM51" in content:
                continue
            # Only touch files that look like they contain mart inventories
            if not re.search(r"\.2byte\s+ITEM_TM", content):
                continue
            # Check for Lilycove content
            if not re.search(r"[Ll]ilycove|[Dd]ept|[Dd]epartment", content):
                continue

            # Insert ITEM_TM51 before the first ITEM_NONE sentinel
            m_sentinel = re.search(r"\.2byte\s+ITEM_NONE", content)
            if m_sentinel:
                insert_pos = m_sentinel.start()
                content = (
                    content[:insert_pos]
                    + "\t.2byte ITEM_TM51\n"
                    + content[insert_pos:]
                )
                write(script_file, content)
                patched_any = True
                print(f"  Patched map script: {script_file.relative_to(poke_dir)}")

    return patched_any


# ---------------------------------------------------------------------------
# Strategy 3 — C source files with inline shop arrays
# ---------------------------------------------------------------------------


def patch_c_sources(poke_dir: Path) -> bool:
    """
    Broad search of C/H files for shop inventory arrays containing ITEM_TM.
    Patches the Lilycove Dept Store array (or any TM-selling mart as fallback).
    """
    candidates = []
    for ext in ("*.c", "*.h"):
        candidates += list((poke_dir / "src").rglob(ext))

    dept_store_file = None
    dept_store_array = None
    any_tm_file = None
    any_tm_array = None

    for src in candidates:
        content = read(src)
        if "ITEM_TM51" in content:
            continue

        # Look for array definitions containing TM items
        for m in re.finditer(
            r"((?:static\s+)?const\s+\w+\s+(\w+)\s*\[\s*\]\s*=\s*\{[^}]*ITEM_TM[^}]*\})",
            content,
            re.DOTALL,
        ):
            array_name = m.group(2)

            # Prefer Lilycove / dept store arrays
            if re.search(r"[Ll]ilycove|[Dd]ept|[Dd]epartment", array_name):
                dept_store_file = src
                dept_store_array = array_name
                break
            elif any_tm_file is None:
                any_tm_file = src
                any_tm_array = array_name

    target_file = dept_store_file or any_tm_file
    target_array = dept_store_array or any_tm_array

    if target_file is None:
        return False

    content = read(target_file)
    content, changed = _add_to_array(content, target_array, "ITEM_TM51")
    if changed:
        write(target_file, content)
        print(f"  Added ITEM_TM51 to {target_array} in {target_file.relative_to(poke_dir)}")
        return True

    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pokeemerald_dir>")
        sys.exit(1)

    poke_dir = Path(sys.argv[1]).resolve()
    if not poke_dir.exists():
        abort(f"pokeemerald directory not found: {poke_dir}")

    print("Patching shops...")

    # Try each strategy in order; stop once one succeeds
    if patch_shops_h(poke_dir):
        print("patch_shops.py done (via shops.h).")
        return

    if patch_map_scripts(poke_dir):
        print("patch_shops.py done (via map scripts).")
        return

    if patch_c_sources(poke_dir):
        print("patch_shops.py done (via C source scan).")
        return

    # Nothing worked — print manual instructions
    print(
        "\n  WARNING: Could not automatically add ITEM_TM51 to any shop.\n"
        "  Manual fix options:\n"
        "\n"
        "  Option A — If shops are in src/data/shops.h or similar:\n"
        "    Find the Lilycove Dept Store item array and add ITEM_TM51\n"
        "    before the ITEM_NONE sentinel.\n"
        "\n"
        "  Option B — If shops are in map scripts (.inc files in data/scripts/):\n"
        "    Find LilycoveCity_DepartmentStore_*_Items and add:\n"
        "        .2byte ITEM_TM51\n"
        "    before the .2byte ITEM_NONE line.\n"
        "\n"
        "  Option C — Give TM51 directly in-game via script instead:\n"
        "    Use SetVar + GiveItem events tied to a map object/NPC.\n"
    )
    print("patch_shops.py done (manual intervention needed for shops).")


if __name__ == "__main__":
    main()
