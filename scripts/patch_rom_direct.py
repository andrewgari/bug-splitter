#!/usr/bin/env python3
"""
patch_rom_direct.py
===================
Directly patches a Moemon Emerald (or any Gen 3 Emerald) ROM to replace
Megahorn with Bug Splitter, then writes an IPS patch file.

Bug Splitter stats:
  Type:     Bug (physical in Gen 3 — uses Atk/Def)
  Power:    200
  Accuracy: 100%
  PP:       15
  Effect:   High critical-hit ratio (same as Slash)
  Contact:  Yes

Why Megahorn?
  - Already a high-powered Bug physical move (slot 224)
  - Already in the learnsets of Heracross, Scyther, Rhyhorn/Rhydon, Seaking
  - Replacing it means those Pokémon get Bug Splitter for free
  - Minimum number of byte edits — no table expansion needed

Usage:
  python3 patch_rom_direct.py --rom moemon_emerald.gba
  python3 patch_rom_direct.py --rom moemon_emerald.gba --out bug_splitter.ips

Outputs:
  <rom_stem>_patched.gba   — patched ROM for testing
  bug_splitter.ips         — IPS patch to distribute
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ROM detection (find move table + name table automatically)
# ---------------------------------------------------------------------------

MOVE_SIZE = 12   # bytes per move entry
NAME_SIZE = 13   # bytes per move name (12 chars + 0xFF terminator)

# Megahorn move ID (same in all clean Gen 3 Emerald ROMs)
MEGAHORN_ID = 224

# Pound's byte signature (used to locate the move table)
# effect=0, power=40, type=Normal(0), acc=100, pp=35, sec=0, tgt=0, pri=0, flags=0x33, pad*3
POUND_SIGNATURE = bytes([0x00, 0x28, 0x00, 0x64, 0x23, 0x00, 0x00, 0x00, 0x33, 0x00, 0x00, 0x00])
MOVE_NONE_ZEROS = bytes(12)

# GBA Pokemon charset encoding
def gba_encode(text: str) -> bytes:
    out = []
    for ch in text:
        if ch == ' ':
            out.append(0x00)
        elif 'A' <= ch <= 'Z':
            out.append(0xBB + ord(ch) - ord('A'))
        elif 'a' <= ch <= 'z':
            out.append(0xD5 + ord(ch) - ord('a'))
        else:
            raise ValueError(f"Cannot encode character: {ch!r}")
    return bytes(out)

def gba_decode(data: bytes) -> str:
    out = []
    for b in data:
        if b == 0xFF:
            break
        elif b == 0x00:
            out.append(' ')
        elif 0xBB <= b <= 0xD4:
            out.append(chr(ord('A') + b - 0xBB))
        elif 0xD5 <= b <= 0xEE:
            out.append(chr(ord('a') + b - 0xD5))
        else:
            out.append('?')
    return ''.join(out)


def find_move_table(rom: bytes) -> int:
    """Locate the move data table by finding MOVE_NONE followed by MOVE_POUND."""
    pattern = MOVE_NONE_ZEROS + POUND_SIGNATURE
    idx = rom.find(pattern)
    if idx == -1:
        raise RuntimeError(
            "Could not locate the move data table.\n"
            "This ROM may not be a standard Gen 3 Emerald-based game."
        )
    return idx  # Points to MOVE_NONE (move ID 0)


def find_name_table(rom: bytes, move_table: int) -> int:
    """
    Locate the move name table by searching for MEGAHORN in all-caps GBA charset.
    Once found, back-calculate the table base from move ID 224.
    """
    megahorn_name = gba_encode("MEGAHORN")
    idx = rom.find(megahorn_name)
    if idx == -1:
        # Try mixed case
        for variant in ["Megahorn", "megahorn"]:
            idx = rom.find(gba_encode(variant))
            if idx != -1:
                break
    if idx == -1:
        raise RuntimeError(
            "Could not locate the move name table (searched for MEGAHORN).\n"
            "Specify --name-table-offset manually if you know the offset."
        )
    return idx - MEGAHORN_ID * NAME_SIZE  # Table base (move[0] name slot)


# ---------------------------------------------------------------------------
# Bug Splitter data
# ---------------------------------------------------------------------------

BUG_SPLITTER_NAME_RAW = "BUG SPLITTER"   # Exactly 12 chars

def build_bug_splitter_move_bytes(existing_flags: int = 0x33) -> bytes:
    """
    Build the 12-byte move entry for Bug Splitter.

    Byte layout (Gen 3 BattleMove struct):
      0: effect        — 0x2B (43) = EFFECT_HIGH_CRITICAL
      1: power         — 0xC8 (200)
      2: type          — 0x06 = Bug
      3: accuracy      — 0x64 (100)
      4: pp            — 0x0F (15)
      5: sec.eff.%     — 0x00
      6: target        — 0x00 (single selected)
      7: priority      — 0x00
      8: flags         — preserved from original (or default 0x33)
      9-11: padding    — 0x00 0x00 0x00
    """
    return bytes([
        0x2B,          # effect: EFFECT_HIGH_CRITICAL
        0xC8,          # power: 200
        0x06,          # type: Bug
        0x64,          # accuracy: 100
        0x0F,          # pp: 15
        0x00,          # secondary effect chance
        0x00,          # target
        0x00,          # priority
        existing_flags,# flags (keep original — typically 0x33)
        0x00, 0x00, 0x00,  # padding
    ])


def build_bug_splitter_name_bytes() -> bytes:
    """Build the 13-byte name entry for Bug Splitter (12 chars + 0xFF)."""
    encoded = gba_encode(BUG_SPLITTER_NAME_RAW)
    assert len(encoded) == 12, f"Name must be exactly 12 chars, got {len(encoded)}"
    return encoded + bytes([0xFF])


# ---------------------------------------------------------------------------
# IPS patch generator
# ---------------------------------------------------------------------------

def create_ips(original: bytes, modified: bytes) -> bytes:
    """Generate an IPS patch (max 16 MB ROMs)."""
    assert len(original) == len(modified), "ROMs must be same size for IPS diff"
    records = []
    i = 0
    n = len(original)
    while i < n:
        if original[i] == modified[i]:
            i += 1
            continue
        start = i
        chunk = bytearray()
        while i < n and original[i] != modified[i] and len(chunk) < 0xFFFF:
            chunk.append(modified[i])
            i += 1
        if start > 0xFFFFFF:
            raise ValueError(f"Offset {start:#010x} exceeds IPS 16 MB limit")
        records.append((start, bytes(chunk)))

    out = bytearray(b"PATCH")
    for offset, data in records:
        out += offset.to_bytes(3, "big")
        out += len(data).to_bytes(2, "big")
        out += data
    out += b"EOF"
    return bytes(out)


# ---------------------------------------------------------------------------
# Verify ROM
# ---------------------------------------------------------------------------

def verify_rom(rom: bytes) -> dict:
    """Check ROM header and return info dict."""
    if len(rom) < 0xC0:
        raise ValueError("File too small to be a GBA ROM")
    title = rom[0xA0:0xAC].decode("ascii", errors="replace").rstrip("\x00")
    code  = rom[0xAC:0xB0].decode("ascii", errors="replace")
    rev   = rom[0xBE]
    return {"title": title, "code": code, "revision": rev, "size": len(rom)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Replace Megahorn with Bug Splitter in a Gen 3 Emerald ROM and create an IPS patch."
    )
    parser.add_argument("--rom", required=True, metavar="PATH", help="Input ROM (.gba)")
    parser.add_argument(
        "--out", default="bug_splitter.ips", metavar="FILE",
        help="Output IPS patch filename (default: bug_splitter.ips)"
    )
    parser.add_argument(
        "--move-id", type=int, default=MEGAHORN_ID, metavar="N",
        help=f"Move slot to replace (default: {MEGAHORN_ID} = Megahorn)"
    )
    parser.add_argument(
        "--name-table-offset", type=lambda x: int(x, 0), default=None,
        metavar="HEX", help="Override name table base offset (hex, e.g. 0x3335A4)"
    )
    parser.add_argument(
        "--move-table-offset", type=lambda x: int(x, 0), default=None,
        metavar="HEX", help="Override move data table base offset (hex, e.g. 0x337DB0)"
    )
    args = parser.parse_args()

    rom_path = Path(args.rom)
    if not rom_path.exists():
        print(f"ERROR: ROM not found: {rom_path}", file=sys.stderr)
        sys.exit(1)

    original = rom_path.read_bytes()
    info = verify_rom(original)
    print(f"ROM : {rom_path.name}")
    print(f"     title={info['title']!r}  code={info['code']!r}  rev={info['revision']}  "
          f"size={info['size'] / 1024 / 1024:.2f} MB")

    rom = bytearray(original)

    # Locate tables
    move_table = args.move_table_offset or find_move_table(bytes(rom))
    name_table = args.name_table_offset or find_name_table(bytes(rom), move_table)
    print(f"Move table : 0x{move_table:08X}")
    print(f"Name table : 0x{name_table:08X}")

    move_id = args.move_id
    move_offset = move_table + move_id * MOVE_SIZE
    name_offset = name_table + move_id * NAME_SIZE

    # Read existing data
    old_move = bytes(rom[move_offset:move_offset + MOVE_SIZE])
    old_name = bytes(rom[name_offset:name_offset + NAME_SIZE])
    existing_name = gba_decode(old_name)
    print(f"\nReplacing move {move_id}: '{existing_name}'")
    print(f"  Move data offset: 0x{move_offset:08X}  bytes: {old_move.hex()}")
    print(f"  Name data offset: 0x{name_offset:08X}  bytes: {old_name.hex()}")
    print(f"  Old stats: eff={old_move[0]} pow={old_move[1]} type={old_move[2]} "
          f"acc={old_move[3]} pp={old_move[4]} flags=0x{old_move[8]:02X}")

    # Build new data
    new_move = build_bug_splitter_move_bytes(existing_flags=old_move[8])
    new_name = build_bug_splitter_name_bytes()
    print("\nBug Splitter stats:")
    print(f"  pow=200  type=Bug(6)  acc=100  pp=15  effect=43(HighCrit)  flags=0x{new_move[8]:02X}")
    print(f"  Name bytes: {new_name.hex()} → '{gba_decode(new_name)}'")

    # Apply patches
    rom[move_offset:move_offset + MOVE_SIZE] = new_move
    rom[name_offset:name_offset + NAME_SIZE] = new_name

    modified = bytes(rom)

    # Write patched ROM
    patched_rom_path = rom_path.with_stem(rom_path.stem + "_patched")
    patched_rom_path.write_bytes(modified)
    print(f"\nPatched ROM written: {patched_rom_path}")

    # Create IPS patch
    ips_data = create_ips(original, modified)
    out_path = Path(args.out)
    out_path.write_bytes(ips_data)

    # Report patch contents
    print(f"IPS patch  written: {out_path}  ({len(ips_data)} bytes)")
    print("\nPatch contains 2 records:")
    print(f"  1. Move data  @ 0x{move_offset:08X}  ({MOVE_SIZE} bytes)")
    print(f"  2. Move name  @ 0x{name_offset:08X}  ({NAME_SIZE} bytes)")
    print(f"\nApply {out_path.name} to '{rom_path.name}' using Floating IPS or Lunar IPS.")

    # Summary
    print("\n--- What changed ---")
    print(f"  Move slot {move_id} ('{existing_name}') → Bug Splitter")
    print( "  Power:    " + f"{old_move[1]} → 200")
    print( "  Accuracy: " + f"{old_move[3]} → 100%")
    print( "  PP:       " + f"{old_move[4]} → 15")
    print( "  Effect:   " + f"{old_move[0]} → 43 (high critical hit)")
    print( "  Type:     Bug (unchanged)")
    print("\n  Pokémon that already knew Megahorn now know Bug Splitter:")
    print("  Heracross, Scyther, Rhyhorn, Rhydon, Seaking (check your hack's learnsets)")


if __name__ == "__main__":
    main()
