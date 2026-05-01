#!/usr/bin/env python3
"""
Bug Splitter Patch Builder for Pokemon Emerald
================================================
Adds TM51 (Bug Splitter) to a clean US Pokemon Emerald ROM.

Bug Splitter stats:
  Type:     Bug (physical in Gen 3)
  Power:    200
  Accuracy: 100%
  PP:       15
  Effect:   High critical hit ratio
  TM:       TM51 — sold in shops for 1000g
  Learns:   All 36 Bug-type Pokemon (via TM only)

Usage:
  python3 build.py --rom /path/to/emerald.gba

Prerequisites:
  - devkitARM (https://devkitpro.org/wiki/Getting_Started)
  - git
  - Python 3.8+
  - flips (optional; Python fallback is built in)

Output:
  bug_splitter.ips  — apply to your Emerald ROM with Floating IPS or Lunar IPS
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

POKEEMERALD_URL = "https://github.com/pret/pokeemerald"
ROOT = Path(__file__).resolve().parent
POKEEMERALD_DIR = ROOT / "pokeemerald"
SCRIPTS_DIR = ROOT / "scripts"

PATCH_SCRIPTS = [
    "patch_moves.py",
    "patch_items.py",
    "patch_learnsets.py",
    "patch_shops.py",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(cmd, *, cwd=None, env=None, check=True):
    """Run a command, echoing it first."""
    display = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else cmd
    print(f"  $ {display}")
    return subprocess.run(cmd, cwd=cwd, env=env, check=check)


def die(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def check_prerequisites():
    missing = []
    if not shutil.which("git"):
        missing.append("git")
    if not shutil.which("arm-none-eabi-gcc") and not _find_devkitarm():
        missing.append(
            "devkitARM  (install from https://devkitpro.org/wiki/Getting_Started)"
        )
    if missing:
        die("Missing prerequisites:\n  " + "\n  ".join(missing))


def _find_devkitarm():
    for candidate in [
        os.environ.get("DEVKITARM", ""),
        "/opt/devkitpro/devkitARM",
        os.path.expanduser("~/devkitpro/devkitARM"),
    ]:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def setup_pokeemerald(skip_clone: bool):
    if skip_clone:
        if not POKEEMERALD_DIR.exists():
            die(f"--skip-clone was set but {POKEEMERALD_DIR} does not exist.")
        print(f"Using existing pokeemerald at {POKEEMERALD_DIR}")
        return

    if POKEEMERALD_DIR.exists():
        print(f"pokeemerald directory already present at {POKEEMERALD_DIR}")
        return

    print("\n--- Cloning pokeemerald ---")
    run(["git", "clone", "--depth=1", POKEEMERALD_URL, str(POKEEMERALD_DIR)])


def apply_patches(skip_patch: bool):
    if skip_patch:
        print("Skipping source patches (--skip-patch).")
        return

    for script_name in PATCH_SCRIPTS:
        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            die(f"Patch script not found: {script_path}")
        print(f"\n--- Applying {script_name} ---")
        run([sys.executable, str(script_path), str(POKEEMERALD_DIR)])


def build_rom(skip_build: bool):
    if skip_build:
        print("Skipping build (--skip-build).")
        return

    devkitarm = _find_devkitarm()
    if not devkitarm:
        die(
            "devkitARM not found. Install from https://devkitpro.org/wiki/Getting_Started\n"
            "Then set the DEVKITPRO environment variable (e.g. export DEVKITPRO=/opt/devkitpro)"
        )

    devkitpro = str(Path(devkitarm).parent)
    env = os.environ.copy()
    env.setdefault("DEVKITPRO", devkitpro)
    env.setdefault("DEVKITARM", devkitarm)
    # Prepend devkitARM bin to PATH so arm-none-eabi-gcc is found
    env["PATH"] = str(Path(devkitarm) / "bin") + ":" + env.get("PATH", "")

    print("\n--- Building pokeemerald (this takes a few minutes) ---")
    result = subprocess.run(
        ["make", "-j4"],
        cwd=str(POKEEMERALD_DIR),
        env=env,
    )
    if result.returncode != 0:
        die("Build failed. Review the errors above.")


def generate_patch(base_rom: Path, output: Path):
    built_rom = POKEEMERALD_DIR / "pokeemerald.gba"
    if not built_rom.exists():
        die(
            f"Built ROM not found at {built_rom}\n"
            "Run without --skip-build, or build pokeemerald manually first."
        )

    print(f"\n--- Generating IPS patch: {output} ---")
    if shutil.which("flips"):
        run(["flips", "--create", "--ips", str(base_rom), str(built_rom), str(output)])
    else:
        print("'flips' not found — using built-in Python IPS generator.")
        _python_ips(base_rom, built_rom, output)

    size_kb = output.stat().st_size / 1024
    print(f"\nPatch written: {output}  ({size_kb:.1f} KB)")


def _python_ips(original: Path, modified: Path, output: Path):
    """Pure-Python IPS patch generator (supports ROMs up to 16 MB)."""
    orig = bytearray(original.read_bytes())
    mod = bytearray(modified.read_bytes())

    # Pad to equal length
    max_len = max(len(orig), len(mod))
    orig += b"\x00" * (max_len - len(orig))
    mod += b"\x00" * (max_len - len(mod))

    records = []
    i = 0
    while i < max_len:
        if orig[i] == mod[i]:
            i += 1
            continue
        start = i
        chunk = bytearray()
        while i < max_len and orig[i] != mod[i] and len(chunk) < 0xFFFF:
            chunk.append(mod[i])
            i += 1
        if start > 0xFFFFFF:
            raise ValueError(
                f"Offset {start:#010x} exceeds the 16 MB IPS limit. "
                "Use BPS format instead (install flips)."
            )
        records.append((start, chunk))

    with open(output, "wb") as f:
        f.write(b"PATCH")
        for offset, data in records:
            f.write(offset.to_bytes(3, "big"))
            f.write(len(data).to_bytes(2, "big"))
            f.write(data)
        f.write(b"EOF")

    changed_bytes = sum(len(d) for _, d in records)
    print(f"  {len(records)} records, {changed_bytes} changed bytes")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build the Bug Splitter (TM51) IPS patch for Pokemon Emerald."
    )
    parser.add_argument(
        "--rom",
        required=True,
        metavar="PATH",
        help="Path to a clean Pokemon Emerald US ROM (.gba)",
    )
    parser.add_argument(
        "--output",
        default="bug_splitter.ips",
        metavar="FILE",
        help="Output IPS patch file (default: bug_splitter.ips)",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Skip cloning pokeemerald (use existing directory)",
    )
    parser.add_argument(
        "--skip-patch",
        action="store_true",
        help="Skip applying source patches (useful for re-builds after manual edits)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the make step (use existing pokeemerald.gba)",
    )
    args = parser.parse_args()

    base_rom = Path(args.rom).resolve()
    if not base_rom.exists():
        die(f"ROM not found: {base_rom}")

    output = Path(args.output).resolve()

    print("=" * 50)
    print("  Bug Splitter Patch Builder")
    print("=" * 50)
    print(f"  Base ROM : {base_rom}")
    print(f"  Output   : {output}")
    print()

    check_prerequisites()
    setup_pokeemerald(args.skip_clone)
    apply_patches(args.skip_patch)
    build_rom(args.skip_build)
    generate_patch(base_rom, output)

    print()
    print("=" * 50)
    print("  Done!")
    print("=" * 50)
    print(f"Apply {output.name} to your Emerald ROM using Floating IPS or Lunar IPS.")
    print("Patch against: clean Pokemon Emerald (US) BPEE0.")


if __name__ == "__main__":
    main()
