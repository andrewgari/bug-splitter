# Bug Splitter — Pokemon Emerald Patch

Adds **TM51 (Bug Splitter)** to Pokemon Emerald.

| Stat | Value |
|------|-------|
| Type | Bug (Physical in Gen 3) |
| Power | 200 |
| Accuracy | 100% |
| PP | 15 |
| Effect | High critical-hit ratio (like Slash) |
| TM | TM51 — sold in shops for **1000g** |
| Compatible | All 36 Bug-type Pokemon |

Bug-type Pokemon that can learn Bug Splitter via TM51:
Caterpie, Metapod, Butterfree, Weedle, Kakuna, Beedrill, Paras, Parasect, Venonat, Venomoth, Scyther, Pinsir, Ledyba, Ledian, Spinarak, Ariados, Yanma, Pineco, Forretress, Scizor, Shuckle, Heracross, Wurmple, Silcoon, Beautifly, Cascoon, Dustox, Surskit, Masquerain, Nincada, Ninjask, Shedinja, Volbeat, Illumise, Anorith, Armaldo

---

## Applying the patch (end users)

1. Download `bug_splitter.ips`
2. Get a clean **Pokemon Emerald US** ROM (`BPEE`, region code `0`)
3. Open **[Floating IPS](https://github.com/Alcaro/Flips)** (or Lunar IPS)
4. Click **Apply Patch** → select `bug_splitter.ips` → select your ROM
5. Load the patched ROM in mGBA, VBA-M, or any GBA emulator

> **Compatibility note:** The patch is generated against a clean Emerald ROM.
> If you stack it with another patch, apply Bug Splitter **last**. Patches that
> modify learnsets, TM items, or shop inventories may conflict.

---

## Building the patch yourself

### Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.8+ | Runs the build script |
| git | Clones pokeemerald |
| devkitARM | ARM cross-compiler for GBA — [install guide](https://devkitpro.org/wiki/Getting_Started) |
| flips *(optional)* | Creates IPS/BPS files — [download](https://github.com/Alcaro/Flips/releases); a Python fallback is built in |

### Steps

```bash
# 1. Install devkitPro / devkitARM (Linux example)
sudo dkp-pacman -S gba-dev

# 2. Export devkitPro path
export DEVKITPRO=/opt/devkitpro
export DEVKITARM=$DEVKITPRO/devkitARM

# 3. Build the patch
python3 build.py --rom /path/to/emerald.gba

# Output: bug_splitter.ips (in the current directory)
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

# Just regenerate patch from an already-built ROM
python3 build.py --rom emerald.gba --skip-clone --skip-patch --skip-build
```

---

## How it works

The build scripts modify these pokeemerald source files:

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

### Adding TM51 (why it needs an HM shift)

pokeemerald stores TM/HM compatibility as a 64-bit bitmask per species:

```
bits 0–49  → TM01–TM50
bits 50–57 → HM01–HM08
bits 58–63 → unused
```

Adding TM51 increments `NUM_TECHNICAL_MACHINES` from 50 to 51.  
pokeemerald defines HM bit positions as `NUM_TECHNICAL_MACHINES + n`, so HMs
automatically shift from bits 50–57 to bits 51–58 at **compile time** — no
manual learnset transformation is needed.

---

## Troubleshooting

**Build fails: `arm-none-eabi-gcc: command not found`**  
Install devkitARM and export `DEVKITPRO`/`DEVKITARM`. See the
[devkitPro getting-started guide](https://devkitpro.org/wiki/Getting_Started).

**`patch_shops.py` warns it couldn't find shop data**  
Shop inventory location varies by pokeemerald version. Manually add
`ITEM_TM51` before the `ITEM_NONE` sentinel in the Lilycove Dept Store
item array, then re-run with `--skip-clone --skip-patch`.

**TM51 taught but has wrong move / wrong Pokemon name shows**  
The move name file was not auto-detected. Search for `gMoveNames` in the
pokeemerald source and add `[MOVE_BUG_SPLITTER] = _("Bug Splitter"),` manually.

**ROM checksum mismatch in emulator**  
Make sure you used the correct US Emerald ROM (internal name `POKEMON EMERALD`,
game code `BPEE`, revision `0`). European and Japanese versions have different
offsets and will not build correctly.
