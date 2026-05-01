#!/usr/bin/env python3
"""
patch_learnsets.py — Add TM51 (Bug Splitter) to all Bug-type Pokemon learnsets.

Changes made:
  src/data/pokemon/tmhm_learnsets.h  (or equivalent)
    - For each of the 36 Bug-type Pokemon: add TM51 / Bug Splitter compatibility

  include/constants/pokemon.h  (or equivalent)
    - If TM index constants (TM51_BUG_SPLITTER) need to be declared, add them

Handles two known pokeemerald learnset formats:
  Format A — TMHM() macro with named TM constants:
      TMHM_LEARNSET(TMHM(TM06_TOXIC) | TMHM(HM01_CUT))
  Format B — Bitfield struct with named boolean fields:
      [SPECIES_X] = { .learnset = { .TOXIC = TRUE, ... } }

Adding TM51 with Format A:
  - Define TM51_BUG_SPLITTER = 50 (0-indexed) in the TM constants block
  - Add | TMHM(TM51_BUG_SPLITTER) to each Bug Pokemon's bitmask
  - Changing NUM_TECHNICAL_MACHINES from 50→51 (done by patch_items.py) already
    shifts HM01–HM08 indices by 1 because HM constants are defined as
    (NUM_TECHNICAL_MACHINES + n) — no manual HM bit shift required.

Adding TM51 with Format B:
  - Add .BUG_SPLITTER = TRUE to each Bug Pokemon's struct entry

Usage:
  python3 patch_learnsets.py <pokeemerald_dir>
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bug-type Pokemon — species names as used in pokeemerald SPECIES_ constants
# ---------------------------------------------------------------------------

BUG_SPECIES = [
    # Gen 1
    "CATERPIE", "METAPOD", "BUTTERFREE",
    "WEEDLE", "KAKUNA", "BEEDRILL",
    "PARAS", "PARASECT",
    "VENONAT", "VENOMOTH",
    "SCYTHER",
    "PINSIR",
    # Gen 2
    "LEDYBA", "LEDIAN",
    "SPINARAK", "ARIADOS",
    "YANMA",
    "PINECO", "FORRETRESS",
    "SCIZOR",
    "SHUCKLE",
    "HERACROSS",
    # Gen 3
    "WURMPLE", "SILCOON", "BEAUTIFLY", "CASCOON", "DUSTOX",
    "SURSKIT", "MASQUERAIN",
    "NINCADA", "NINJASK", "SHEDINJA",
    "VOLBEAT", "ILLUMISE",
    "ANORITH", "ARMALDO",
]

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
# Locate learnset file
# ---------------------------------------------------------------------------

LEARNSET_CANDIDATES = [
    Path("src") / "data" / "pokemon" / "tmhm_learnsets.h",
    Path("src") / "data" / "tmhm_learnsets.h",
    Path("src") / "data" / "pokemon" / "learnsets.h",
]


def find_learnset_file(poke_dir: Path) -> Path:
    for rel in LEARNSET_CANDIDATES:
        p = poke_dir / rel
        if p.exists():
            c = read(p)
            if "SPECIES_" in c and ("TMHM" in c or "learnset" in c.lower()):
                return p
    # Broader search
    for h in sorted((poke_dir / "src").rglob("*.h")):
        c = read(h)
        if "SPECIES_CATERPIE" in c and ("TMHM" in c or ".learnset" in c):
            return h
    return None


# ---------------------------------------------------------------------------
# Detect learnset format
# ---------------------------------------------------------------------------


def detect_format(content: str) -> str:
    """
    Returns 'macro'   — TMHM() macro format
            'struct'  — bitfield struct format
            'unknown' — could not determine
    """
    if re.search(r"TMHM_LEARNSET\s*\(", content):
        return "macro"
    if re.search(r"\.learnset\s*=\s*\{", content):
        return "struct"
    return "unknown"


# ---------------------------------------------------------------------------
# Format A — TMHM() macro format
# ---------------------------------------------------------------------------


def patch_tmhm_constants(poke_dir: Path):
    """
    Add TM51_BUG_SPLITTER = 50 to the TM index constants block.
    These constants are typically in include/constants/pokemon.h or items.h
    alongside other TM_ defines.
    """
    # Patterns to search for existing TM constants
    candidates = [
        poke_dir / "include" / "constants" / "pokemon.h",
        poke_dir / "include" / "constants" / "items.h",
        poke_dir / "include" / "constants" / "moves.h",
    ]

    for path in candidates:
        if not path.exists():
            continue
        content = read(path)
        # Look for TM50 index constant (named TM50_OVERHEAT or similar)
        m = re.search(r"#define TM50_\w+\s+(\d+)", content)
        if m:
            if "TM51_BUG_SPLITTER" in content:
                print(f"  TM51_BUG_SPLITTER already defined in {path}")
                return
            tm50_index = int(m.group(1))
            tm51_index = tm50_index + 1
            # Insert TM51 after TM50 definition
            content = re.sub(
                r"(#define TM50_\w+\s+\d+)",
                f"\\1\n#define TM51_BUG_SPLITTER    {tm51_index}",
                content,
            )
            write(path, content)
            print(f"  TM51_BUG_SPLITTER = {tm51_index}")
            return

    print(
        "  NOTE: TM index constants (TM50_OVERHEAT etc.) not found — "
        "TM51 may be auto-indexed via item ID arithmetic. "
        "No extra constant definition needed."
    )


def _make_tmhm_addition(content: str) -> str:
    """Return the token to add: TMHM(TM51_BUG_SPLITTER) or equivalent."""
    # If format uses ITEM_TM51-style identifiers
    if "TMHM(ITEM_TM" in content:
        return "TMHM(ITEM_TM51)"
    # If format uses TM51_BUG_SPLITTER constants
    if re.search(r"TMHM\(TM\d+_\w+\)", content):
        return "TMHM(TM51_BUG_SPLITTER)"
    # Generic fallback
    return "TMHM(TM51_BUG_SPLITTER)"


def patch_macro_format(content: str, species: str) -> tuple[str, bool]:
    """
    Find SPECIES_X's TMHM_LEARNSET(...) entry and append the TM51 bit.
    Returns (updated_content, did_change).
    """
    # Pattern: [SPECIES_X] = TMHM_LEARNSET( ... ),
    # Also handles multi-line with | operators
    pattern = rf"(\[SPECIES_{re.escape(species)}\]\s*=\s*TMHM_LEARNSET\s*\()(.*?)(\))"
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        return content, False

    existing_body = m.group(2)
    addition = _make_tmhm_addition(content)

    if addition in existing_body or "TM51_BUG_SPLITTER" in existing_body:
        return content, False  # Already has it

    # Append the new bit to the body
    if existing_body.strip() == "0" or existing_body.strip() == "":
        new_body = f"\n        {addition}\n    "
    else:
        # Strip trailing whitespace/newlines from body and append with |
        stripped = existing_body.rstrip()
        new_body = stripped + f" |\n        {addition}\n    "

    new_entry = m.group(1) + new_body + m.group(3)
    content = content[: m.start()] + new_entry + content[m.end():]
    return content, True


# ---------------------------------------------------------------------------
# Format B — bitfield struct format
# ---------------------------------------------------------------------------


def patch_struct_format(content: str, species: str) -> tuple[str, bool]:
    """
    Find [SPECIES_X] = { .learnset = { ... } } and add .BUG_SPLITTER = TRUE.
    Returns (updated_content, did_change).
    """
    pattern = rf"(\[SPECIES_{re.escape(species)}\]\s*=\s*\{{[^}}]*\.learnset\s*=\s*\{{)(.*?)(\}})"
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        return content, False

    existing_body = m.group(2)
    if "BUG_SPLITTER" in existing_body:
        return content, False

    # Append .BUG_SPLITTER = TRUE before the closing }
    new_body = existing_body.rstrip() + "\n        .BUG_SPLITTER = TRUE,\n    "
    new_entry = m.group(1) + new_body + m.group(3)
    content = content[: m.start()] + new_entry + content[m.end():]
    return content, True


# ---------------------------------------------------------------------------
# Format: unknown — attempt both, warn if neither works
# ---------------------------------------------------------------------------


def patch_unknown_format(content: str, species: str) -> tuple[str, bool]:
    # Try macro first
    new_content, changed = patch_macro_format(content, species)
    if changed:
        return new_content, True
    # Try struct
    new_content, changed = patch_struct_format(content, species)
    if changed:
        return new_content, True
    return content, False


# ---------------------------------------------------------------------------
# Main learnset patching
# ---------------------------------------------------------------------------


def patch_learnsets(poke_dir: Path):
    learnset_file = find_learnset_file(poke_dir)
    if learnset_file is None:
        abort(
            "Could not locate the TMHM learnset file.\n"
            "Expected one of:\n"
            "  src/data/pokemon/tmhm_learnsets.h\n"
            "  src/data/tmhm_learnsets.h\n"
            "  src/data/pokemon/learnsets.h\n"
            "Manually add TM51 / Bug Splitter to all Bug-type Pokemon."
        )

    content = read(learnset_file)
    fmt = detect_format(content)
    print(f"  Detected learnset format: {fmt}")

    if fmt == "macro":
        patch_tmhm_constants(poke_dir)
        patch_fn = patch_macro_format
    elif fmt == "struct":
        patch_fn = patch_struct_format
    else:
        print("  WARNING: Unknown learnset format — attempting heuristic patches.")
        patch_fn = patch_unknown_format

    patched_count = 0
    skipped = []

    for species in BUG_SPECIES:
        content, changed = patch_fn(content, species)
        if changed:
            patched_count += 1
        else:
            # Species entry may not exist (e.g., not in this Emerald version)
            if f"SPECIES_{species}" not in content:
                skipped.append(species)
            # else: already had TM51 — fine

    write(learnset_file, content)
    print(f"  Added TM51 compatibility to {patched_count} Bug-type Pokemon.")

    if skipped:
        print(
            f"  NOTE: The following species were not found in {learnset_file.name}\n"
            f"  and may need to be patched manually: {', '.join(skipped)}"
        )


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

    print("Patching learnsets...")
    patch_learnsets(poke_dir)
    print("patch_learnsets.py done.")


if __name__ == "__main__":
    main()
