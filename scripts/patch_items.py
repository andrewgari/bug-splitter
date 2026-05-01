#!/usr/bin/env python3
"""
patch_items.py — Add TM51 (Bug Splitter) item to pokeemerald source.

Changes made:
  include/constants/items.h
    - Increment NUM_TECHNICAL_MACHINES from 50 to 51
    - Insert ITEM_TM51 = <value> between ITEM_TM50 and ITEM_HM01
    - Shift all ITEM_HM01..ITEM_HM08 values up by 1

  <items data file>  (auto-detected)
    - Append TM51 item entry (name "TM51", price 1000, pocket TM_HM)

  <gTMHMMoves array>  (auto-detected, usually src/pokemon.c or src/data/tmhm_data.h)
    - Append MOVE_BUG_SPLITTER as TM51 entry

  <item descriptions file>  (auto-detected)
    - Append Bug Splitter description string

Usage:
  python3 patch_items.py <pokeemerald_dir>
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Item data template — mirrors the TM50 entry format
# ---------------------------------------------------------------------------

# Description string (max ~40 chars for item desc in Gen 3)
BUG_SPLITTER_DESC = "A powerful Bug-type move\\nwith a high critical-hit ratio."

TM51_ITEM_ENTRY = """
    [ITEM_TM51] =
    {
        .name = _("TM51"),
        .itemId = ITEM_TM51,
        .price = 1000,
        .description = sBugSplitterTMDesc,
        .pocket = POCKET_TM_HM,
        .type = ITEM_USE_PARTY_MENU,
        .fieldUseFunc = ItemUseOutOfBattle_TMHM,
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
# Step 1 — include/constants/items.h
# ---------------------------------------------------------------------------


def patch_items_h(poke_dir: Path):
    items_h = poke_dir / "include" / "constants" / "items.h"
    if not items_h.exists():
        abort(f"Could not find {items_h}")

    content = read(items_h)

    if "ITEM_TM51" in content:
        print(f"  Already patched: {items_h}")
        return

    # ---- 1a. Find ITEM_TM50 value ----------------------------------------
    m = re.search(r"#define ITEM_TM50\s+(\d+)", content)
    if not m:
        abort(f"Could not find ITEM_TM50 in {items_h}")
    tm50_val = int(m.group(1))
    tm51_val = tm50_val + 1

    # ---- 1b. Find ITEM_HM01 value (should currently equal tm51_val) -------
    m_hm01 = re.search(r"#define ITEM_HM01\s+(\d+)", content)
    if not m_hm01:
        abort(f"Could not find ITEM_HM01 in {items_h}")
    hm01_old = int(m_hm01.group(1))

    if hm01_old != tm51_val:
        print(
            f"  WARNING: ITEM_HM01 ({hm01_old}) is not immediately after "
            f"ITEM_TM50 ({tm50_val}). Inserting TM51 anyway but verify manually."
        )

    # ---- 1c. Shift HM item IDs up by 1 ------------------------------------
    # Process HM01..HM08 from highest to lowest to avoid double-patching
    for i in range(8, 0, -1):
        hm_name = f"ITEM_HM{i:02d}"
        m_hm = re.search(rf"(#define {re.escape(hm_name)}\s+)(\d+)", content)
        if not m_hm:
            print(f"  WARNING: {hm_name} not found — skipping shift for this HM.")
            continue
        old_val = int(m_hm.group(2))
        new_val = old_val + 1
        content = content.replace(
            m_hm.group(0),
            f"{m_hm.group(1)}{new_val}",
            1,
        )

    # ---- 1d. Insert ITEM_TM51 after ITEM_TM50 line ------------------------
    content = re.sub(
        r"(#define ITEM_TM50\s+\d+)",
        f"\\1\n#define ITEM_TM51         {tm51_val}",
        content,
    )

    # ---- 1e. Increment NUM_TECHNICAL_MACHINES ------------------------------
    m_num = re.search(r"(#define NUM_TECHNICAL_MACHINES\s+)(\d+)", content)
    if m_num:
        old_num = int(m_num.group(2))
        content = content.replace(
            m_num.group(0),
            f"{m_num.group(1)}{old_num + 1}",
            1,
        )
        print(f"  NUM_TECHNICAL_MACHINES: {old_num} → {old_num + 1}")
    else:
        print(
            "  WARNING: NUM_TECHNICAL_MACHINES not found in items.h — "
            "search for it in other headers and bump it to 51 manually."
        )

    write(items_h, content)
    print(f"  ITEM_TM51 = {tm51_val}  (HM items shifted up by 1)")


# ---------------------------------------------------------------------------
# Step 2 — Item data (name, price, pocket, etc.)
# ---------------------------------------------------------------------------

ITEM_DATA_CANDIDATES = [
    Path("src") / "data" / "items.h",
    Path("src") / "data" / "item_data.h",
    Path("src") / "data" / "items" / "items.h",
]


def _find_item_data_file(poke_dir: Path) -> Path:
    for rel in ITEM_DATA_CANDIDATES:
        p = poke_dir / rel
        if p.exists() and "ITEM_TM50" in read(p):
            return p
    # Fallback: search src/ for the file containing ITEM_TM50 struct entry
    for h in sorted((poke_dir / "src").rglob("*.h")):
        c = read(h)
        if "ITEM_TM50" in c and "POCKET_TM_HM" in c:
            return h
    return None


def patch_item_data(poke_dir: Path):
    data_file = _find_item_data_file(poke_dir)
    if data_file is None:
        print(
            "  WARNING: Could not locate item data file.\n"
            "  Manually append TM51 item entry (see TM50 for format):\n"
            '    name="TM51", price=1000, pocket=POCKET_TM_HM, type=ITEM_USE_PARTY_MENU'
        )
        return

    content = read(data_file)
    if "ITEM_TM51" in content:
        print(f"  Already patched: {data_file}")
        return

    # Also add the description constant before the item data array
    desc_line = f'static const u8 sBugSplitterTMDesc[] = _("{BUG_SPLITTER_DESC}");\n'

    # Find a description string for TM50 and insert our desc after it
    m_desc = re.search(r"(static const u8 s\w+Desc\[\] = _\(\"[^\"]*\"\);)\n", content)
    if m_desc:
        # Insert our description near other TM descriptions
        # Find TM50's description specifically
        m_tm50_desc = re.search(
            r"(static const u8 s(?:TM50|Overheat)\w*Desc\[\] = _\(\"[^\"]*\"\);)\n",
            content,
        )
        if m_tm50_desc:
            content = content.replace(
                m_tm50_desc.group(0),
                m_tm50_desc.group(0) + desc_line,
                1,
            )
        else:
            # Just insert after the last description we found
            content = content.replace(
                m_desc.group(0),
                m_desc.group(0) + desc_line,
                1,
            )
    else:
        # No desc pattern found — prepend to file
        content = desc_line + content

    # Insert TM51 item entry before the closing }; of the item array
    if not re.search(r"\};\s*$", content, re.MULTILINE):
        print(
            f"  WARNING: Could not find closing of item array in {data_file}.\n"
            "  Manually append the TM51 item entry."
        )
        write(data_file, content)  # Still save the description
        return

    content = re.sub(
        r"(\};\s*)$",
        TM51_ITEM_ENTRY + r"\1",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    write(data_file, content)


# ---------------------------------------------------------------------------
# Step 3 — gTMHMMoves[] (maps TM slot → move ID)
# ---------------------------------------------------------------------------

TMHMMOVES_CANDIDATES = [
    Path("src") / "pokemon.c",
    Path("src") / "data" / "pokemon" / "tmhm_moves.h",
    Path("src") / "data" / "tmhm_moves.h",
]


def _find_tmhmmoves_file(poke_dir: Path):
    """Return (path, array_name) for the file containing the TM→move mapping."""
    for rel in TMHMMOVES_CANDIDATES:
        p = poke_dir / rel
        if p.exists():
            c = read(p)
            if "gTMHMMoves" in c or "MOVE_OVERHEAT" in c:
                return p
    # Search broadly
    for src in sorted((poke_dir / "src").rglob("*.c")) + sorted(
        (poke_dir / "src").rglob("*.h")
    ):
        c = read(src)
        if "gTMHMMoves" in c:
            return src
    return None


def patch_tmhmmoves(poke_dir: Path):
    tm_file = _find_tmhmmoves_file(poke_dir)
    if tm_file is None:
        print(
            "  WARNING: Could not locate gTMHMMoves array.\n"
            "  Manually add MOVE_BUG_SPLITTER as the 51st entry in the TM move list."
        )
        return

    content = read(tm_file)
    if "MOVE_BUG_SPLITTER" in content:
        print(f"  Already patched: {tm_file}")
        return

    # Find the gTMHMMoves array and insert before its closing };
    # Pattern: the array ends after the last HM move entry
    # We want to insert MOVE_BUG_SPLITTER BEFORE the HM moves (as TM51)
    # The array layout is: TM01...TM50, HM01...HM08
    # We need to insert after TM50 (MOVE_OVERHEAT) and before HM01 (MOVE_CUT)

    # Try to find MOVE_OVERHEAT as the last TM entry
    m_overheat = re.search(
        r"([ \t]*/\*\s*TM50\s*\*/\s*MOVE_OVERHEAT,?\s*\n)",
        content,
    )
    if m_overheat:
        content = content.replace(
            m_overheat.group(1),
            m_overheat.group(1) + "    /* TM51 */ MOVE_BUG_SPLITTER,\n",
            1,
        )
        write(tm_file, content)
        return

    # Fallback: find the array by name and insert after TM50 comment
    m_array = re.search(r"(gTMHMMoves\s*\[\s*\][^{]*\{[^}]*)(MOVE_OVERHEAT)", content)
    if m_array:
        # Find the MOVE_OVERHEAT entry and add after it
        content = re.sub(
            r"(MOVE_OVERHEAT,?\s*\n)",
            r"\1    /* TM51 */ MOVE_BUG_SPLITTER,\n",
            content,
            count=1,
        )
        write(tm_file, content)
        return

    # Last resort: insert before closing of gTMHMMoves array
    # Try to identify the array boundaries
    m_array_start = re.search(r"gTMHMMoves", content)
    if m_array_start:
        # Find the }; after the array start
        after_array = content[m_array_start.start():]
        m_close = re.search(r"\};\s*\n", after_array)
        if m_close:
            insert_pos = m_array_start.start() + m_close.start()
            content = (
                content[:insert_pos]
                + "    /* TM51 */ MOVE_BUG_SPLITTER,\n"
                + content[insert_pos:]
            )
            write(tm_file, content)
            return

    print(
        f"  WARNING: Could not automatically patch gTMHMMoves in {tm_file}.\n"
        "  Manually add:  /* TM51 */ MOVE_BUG_SPLITTER,\n"
        "  after the TM50 (MOVE_OVERHEAT) entry and before the HM entries."
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

    print("Patching items...")
    patch_items_h(poke_dir)
    patch_item_data(poke_dir)
    patch_tmhmmoves(poke_dir)
    print("patch_items.py done.")


if __name__ == "__main__":
    main()
