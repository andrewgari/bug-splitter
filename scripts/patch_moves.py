#!/usr/bin/env python3
"""
patch_moves.py — Add Bug Splitter move to pokeemerald source.

Changes made:
  include/constants/moves.h
    - Add:  #define MOVE_BUG_SPLITTER 355
    - Bump: MOVES_COUNT 355 → 356

  src/data/battle_moves.h
    - Append Bug Splitter entry to gBattleMoves[] array

  <move names file>  (auto-detected)
    - Append: [MOVE_BUG_SPLITTER] = _("Bug Splitter"),

Usage:
  python3 patch_moves.py <pokeemerald_dir>
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Move data
# ---------------------------------------------------------------------------

BUG_SPLITTER_ENTRY = """
    [MOVE_BUG_SPLITTER] =
    {
        .effect = EFFECT_HIGH_CRITICAL,
        .power = 200,
        .type = TYPE_BUG,
        .accuracy = 100,
        .pp = 15,
        .secondaryEffectChance = 0,
        .target = MOVE_TARGET_SELECTED,
        .priority = 0,
        .flags = FLAG_MAKES_CONTACT | FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED | FLAG_KINGS_ROCK_AFFECTED,
    },
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"  Updated: {path}")


def abort(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1 — include/constants/moves.h
# ---------------------------------------------------------------------------


def patch_moves_h(poke_dir: Path):
    moves_h = poke_dir / "include" / "constants" / "moves.h"
    if not moves_h.exists():
        abort(f"Could not find {moves_h}")

    content = read(moves_h)

    # Guard: already patched?
    if "MOVE_BUG_SPLITTER" in content:
        print(f"  Already patched: {moves_h}")
        return

    # Find current MOVES_COUNT value
    m = re.search(r"#define MOVES_COUNT\s+(\d+)", content)
    if not m:
        abort(f"Could not find MOVES_COUNT in {moves_h}")

    current_count = int(m.group(1))
    bug_splitter_id = current_count          # New move gets the current count as its ID
    new_count = current_count + 1

    # Insert MOVE_BUG_SPLITTER just before MOVES_COUNT
    content = re.sub(
        r"(#define MOVES_COUNT\s+\d+)",
        f"#define MOVE_BUG_SPLITTER {bug_splitter_id}\n\\1",
        content,
    )

    # Bump MOVES_COUNT
    content = re.sub(
        r"#define MOVES_COUNT\s+\d+",
        f"#define MOVES_COUNT {new_count}",
        content,
    )

    write(moves_h, content)
    print(f"  MOVE_BUG_SPLITTER = {bug_splitter_id}, MOVES_COUNT = {new_count}")


# ---------------------------------------------------------------------------
# Step 2 — src/data/battle_moves.h
# ---------------------------------------------------------------------------


def patch_battle_moves(poke_dir: Path):
    battle_h = poke_dir / "src" / "data" / "battle_moves.h"
    if not battle_h.exists():
        abort(f"Could not find {battle_h}")

    content = read(battle_h)

    if "MOVE_BUG_SPLITTER" in content:
        print(f"  Already patched: {battle_h}")
        return

    # The array ends with };  — insert Bug Splitter entry just before the final };
    # We look for the last }; in the file (end of gBattleMoves array)
    if not re.search(r"\};\s*$", content, re.MULTILINE):
        abort(
            f"Could not find closing '}}; ' of gBattleMoves array in {battle_h}\n"
            "The file format may have changed. Edit it manually:\n"
            "  Append the Bug Splitter entry before the final '}; '"
        )

    # Insert before the very last };
    content = re.sub(
        r"(\};\s*)$",
        BUG_SPLITTER_ENTRY + r"\1",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    write(battle_h, content)


# ---------------------------------------------------------------------------
# Step 3 — Move names
# ---------------------------------------------------------------------------


# Candidate file paths for move name arrays (checked in order)
MOVE_NAME_CANDIDATES = [
    Path("src") / "data" / "text" / "move_names.h",
    Path("src") / "data" / "pokemon" / "move_names.h",
    Path("src") / "data" / "move_names.h",
    Path("src") / "data" / "battle_moves.h",  # Some versions embed names here
]


def _find_move_names_file(poke_dir: Path) -> Path:
    """Locate the file containing the move names array."""
    for rel in MOVE_NAME_CANDIDATES:
        p = poke_dir / rel
        if p.exists():
            c = read(p)
            # Confirm it has actual move name entries
            if "_(" in c and "MOVE_" in c:
                return p

    # Fall back: search all .h files under src/ for gMoveNames
    for h in sorted((poke_dir / "src").rglob("*.h")):
        c = read(h)
        if "gMoveNames" in c and "_(" in c:
            return h

    return None


def patch_move_names(poke_dir: Path):
    names_file = _find_move_names_file(poke_dir)
    if names_file is None:
        print(
            "  WARNING: Could not locate the move names file.\n"
            '  Manually add:  [MOVE_BUG_SPLITTER] = _("Bug Splitter"),\n'
            "  to your move names array."
        )
        return

    content = read(names_file)

    if "MOVE_BUG_SPLITTER" in content:
        print(f"  Already patched: {names_file}")
        return

    # Insert before the closing }; of the names array
    if not re.search(r"\};\s*$", content, re.MULTILINE):
        print(
            f"  WARNING: Could not find closing of names array in {names_file}.\n"
            '  Manually add:  [MOVE_BUG_SPLITTER] = _("Bug Splitter"),'
        )
        return

    content = re.sub(
        r"(\};\s*)$",
        '    [MOVE_BUG_SPLITTER] = _("Bug Splitter"),\n' + r"\1",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    write(names_file, content)


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

    print("Patching moves...")
    patch_moves_h(poke_dir)
    patch_battle_moves(poke_dir)
    patch_move_names(poke_dir)
    print("patch_moves.py done.")


if __name__ == "__main__":
    main()
