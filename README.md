# Bug Splitter — Pokemon Emerald Patch

> **Fan project — not affiliated with or endorsed by Nintendo, Creatures Inc., or Game Freak.**
> Pokemon is a trademark of Nintendo. This project does not distribute any ROM files or copyrighted game assets.

A small fan-made patch for **Pokemon Emerald** that adds a brand new move: **Bug Splitter**.

---

## What is Bug Splitter?

Bug Splitter is a powerful new physical move exclusive to Bug-type Pokemon. Think of it as the Bug type's answer to Hyper Beam — but with a high chance to land a critical hit, like Slash.

| | |
|---|---|
| **Type** | Bug |
| **Power** | 200 |
| **Accuracy** | 100% |
| **PP** | 15 |
| **Effect** | High critical-hit ratio |
| **How to get** | Buy TM51 from shops for 1,000 |

Every Bug-type Pokemon in the game can learn it — all 36 of them, from Caterpie all the way to Armaldo.

---

## How to install

You'll need two things before you start:

1. **The patch file** — download `bug_splitter.ips` from this page
2. **A patching tool** — download [Floating IPS](https://github.com/Alcaro/Flips) (free, Windows/Mac/Linux)
3. **A clean Pokemon Emerald ROM** — this needs to be the US version (you'll need to source this yourself)

**Steps:**

1. Open Floating IPS
2. Click **Apply Patch**
3. Select `bug_splitter.ips` when asked for the patch
4. Select your Emerald ROM when asked for the file to patch
5. Load the newly patched ROM in your emulator and enjoy!

> **Stacking patches?** If you're combining this with other Emerald patches, apply Bug Splitter **last**. Patches that change moves, TMs, or shop items may conflict.

---

## Common issues

**The emulator says the ROM is corrupted or has a bad checksum**
Make sure you're using the **US version** of Pokemon Emerald (the cartridge says "BPEE" on the back). European and Japanese versions are laid out differently and won't work.

**TM51 teaches the wrong move, or a Pokemon's name looks garbled**
The patch may not have applied cleanly. Try re-downloading `bug_splitter.ips` and applying it again to a fresh, unmodified ROM.

---

## Which Pokemon can learn it?

All 36 Bug-type Pokemon available in Emerald:

Caterpie, Metapod, Butterfree, Weedle, Kakuna, Beedrill, Paras, Parasect, Venonat, Venomoth, Scyther, Pinsir, Ledyba, Ledian, Spinarak, Ariados, Yanma, Pineco, Forretress, Scizor, Shuckle, Heracross, Wurmple, Silcoon, Beautifly, Cascoon, Dustox, Surskit, Masquerain, Nincada, Ninjask, Shedinja, Volbeat, Illumise, Anorith, Armaldo

---

<details>
<summary>Developer / build-it-yourself info</summary>

### Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.8+ | Runs the build script |
| git | Clones pokeemerald |
| devkitARM | ARM cross-compiler for GBA — [install guide](https://devkitpro.org/wiki/Getting_Started) |
| flips *(optional)* | Creates IPS/BPS files — [download](https://github.com/Alcaro/Flips/releases); a Python fallback is built in |

### Build

```bash
# 1. Install devkitPro / devkitARM (Linux example)
sudo dkp-pacman -S gba-dev

# 2. Export devkitPro path
export DEVKITPRO=/opt/devkitpro
export DEVKITARM=$DEVKITPRO/devkitARM

# 3. Build the patch
python3 build.py --rom /path/to/emerald.gba

# Output: bug_splitter.ips
```

### Options

```
python3 build.py --rom <ROM> [options]

  --rom FILE        Path to clean Pokemon Emerald US ROM  (required)
  --output FILE     Output patch filename  (default: bug_splitter.ips)
  --skip-clone      Use existing pokeemerald/ directory
  --skip-patch      Skip source patches (re-use previously patched source)
  --skip-build      Skip make step (use existing pokeemerald/pokeemerald.gba)
```

### Iterative workflow

```bash
# First run (clones + patches + builds)
python3 build.py --rom emerald.gba

# After manual source edits (skip clone + patch steps)
python3 build.py --rom emerald.gba --skip-clone --skip-patch

# Just regenerate the patch from an already-built ROM
python3 build.py --rom emerald.gba --skip-clone --skip-patch --skip-build
```

### Source changes

| File | Change |
|------|--------|
| `include/constants/moves.h` | Add `MOVE_BUG_SPLITTER = 355`, bump `MOVES_COUNT` to 356 |
| `src/data/battle_moves.h` | Add Bug Splitter entry to `gBattleMoves[]` |
| *(move names file)* | Add `"Bug Splitter"` name string |
| `include/constants/items.h` | Add `ITEM_TM51`, shift `ITEM_HM01–HM08` up by 1, bump `NUM_TECHNICAL_MACHINES` to 51 |
| *(items data file)* | Add TM51 item entry (price 1000, pocket TM/HM) |
| `src/pokemon.c` | Append `MOVE_BUG_SPLITTER` to `gTMHMMoves[]` as slot 51 |
| `src/data/pokemon/tmhm_learnsets.h` | Grant TM51 compatibility to all 36 Bug-type Pokemon |
| *(shop data)* | Add `ITEM_TM51` to Lilycove Dept Store (and other TM-selling marts) |

pokeemerald stores TM/HM compatibility as a 64-bit bitmask per species (`bits 0–49` = TM01–50, `bits 50–57` = HM01–08). Adding TM51 increments `NUM_TECHNICAL_MACHINES` from 50 to 51, which shifts HM bit positions automatically at compile time — no manual learnset transformation needed.

### Build troubleshooting

**`arm-none-eabi-gcc: command not found`**  
Install devkitARM and export `DEVKITPRO`/`DEVKITARM`. See the [devkitPro getting-started guide](https://devkitpro.org/wiki/Getting_Started).

**`patch_shops.py` warns it couldn't find shop data**  
Shop inventory location varies by pokeemerald version. Manually add `ITEM_TM51` before the `ITEM_NONE` sentinel in the Lilycove Dept Store item array, then re-run with `--skip-clone --skip-patch`.

**TM51 taught but has wrong move / wrong Pokemon name shows**  
The move name file was not auto-detected. Search for `gMoveNames` in the pokeemerald source and add `[MOVE_BUG_SPLITTER] = _("Bug Splitter"),` manually.

</details>
