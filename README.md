# Bug Splitter — Pokemon Emerald Patch

> **Fan project — not affiliated with or endorsed by Nintendo, Creatures Inc., or Game Freak.**  
> Pokémon is a trademark of Nintendo. This project does not distribute ROM files or copyrighted game assets.

A fan-made patch for **Pokémon Emerald** (and Emerald-based ROM hacks) that replaces HM01 Cut with a powerful new Bug-type move: **Bug Splitter**.

---

## The move

Bug Splitter replaces Cut in battle. It keeps everything that makes Cut useful on the overworld — trees still get cut — while turning the otherwise forgettable HM into one of the strongest physical moves in the game.

| | |
|---|---|
| **Type** | Bug (Physical — uses Atk/Def in Gen 3) |
| **Power** | 200 |
| **Accuracy** | 100% |
| **PP** | 15 |
| **Effect** | High critical-hit ratio (same stage as Slash) |
| **Makes contact** | Yes |
| **How to get** | Teach HM01 to any compatible Pokémon |
| **Overworld** | Still cuts small trees |

Because Bug Splitter occupies **move slot 15** (the same slot as Cut), the HM01 overworld effect works without any extra changes. The game engine checks whether a party Pokémon knows *move #15*, not what that move is called or what type it is.

---

## Compatibility

### Tested ROMs

| ROM | Version | Result |
|-----|---------|--------|
| Moemon Emerald Vanilla+ | v1.1.0 | ✅ Working |

### Other Emerald-based ROMs

`patch_rom_direct.py` locates the move data and name tables by searching for known byte signatures rather than using fixed offsets. This means it works on ROMs where the tables have moved due to other patches, as long as the Gen 3 Emerald move structure is intact.

If your ROM is heavily modified (custom move engines, expanded move counts, etc.) the script will report clearly if it cannot find the expected tables.

---

## Applying the patch (end users)

Patching requires a tool and a compatible ROM. No ROM files are distributed here.

**Tools:**
- [Floating IPS](https://github.com/Alcaro/Flips/releases) — free, Windows / Mac / Linux
- Your own copy of the target ROM

**Steps:**

1. Download `bug_splitter.ips` from the Releases page
2. Open Floating IPS and click **Apply Patch**
3. Select `bug_splitter.ips` when prompted for the patch file
4. Select your ROM when prompted for the file to patch
5. Load the output ROM in your emulator

> The included `bug_splitter.ips` targets **Moemon Emerald Vanilla+ v1.1.0**.  
> For a different ROM, generate a new patch using `patch_rom_direct.py` (see below).

---

## Which Pokémon can learn Bug Splitter?

Any Pokémon that can learn **HM01** in your ROM. In standard Emerald this includes most Bug-type Pokémon and many others. The full list of Bug-type Pokémon available in the National Dex through Generation III:

**Gen 1:** Caterpie, Metapod, Butterfree, Weedle, Kakuna, Beedrill, Paras, Parasect, Venonat, Venomoth, Scyther, Pinsir

**Gen 2:** Ledyba, Ledian, Spinarak, Ariados, Yanma, Pineco, Forretress, Scizor, Shuckle, Heracross

**Gen 3:** Wurmple, Silcoon, Beautifly, Cascoon, Dustox, Surskit, Masquerain, Nincada, Ninjask, Shedinja, Volbeat, Illumise, Anorith, Armaldo

Note: HM01 learnability is determined by your specific ROM's compatibility tables, not by Bug Splitter itself. If a Pokémon could not learn Cut in your ROM, it cannot learn Bug Splitter either.

---

## Generating a patch for your ROM

Use `patch_rom_direct.py` to create a patch tailored to any Emerald-based ROM.

**Requirements:** Python 3.8+, no other dependencies.

```bash
python3 scripts/patch_rom_direct.py --rom your_emerald_hack.gba
```

This produces:
- `your_emerald_hack_patched.gba` — patched ROM for testing
- `bug_splitter.ips` — IPS patch to distribute

**Options:**

```
--rom FILE              Input ROM (required)
--out FILE              Output IPS filename (default: bug_splitter.ips)
--move-id N             Move slot to replace (default: 15 = Cut)
--move-table-offset HEX Override move data table base (e.g. 0x337DB0)
--name-table-offset HEX Override move name table base (e.g. 0x3335A4)
```

The script auto-detects both table offsets by searching for the known byte signature of MOVE_NONE + MOVE_POUND and the all-caps "MEGAHORN" name string. Pass the override flags if auto-detection fails on a heavily modified ROM.

---

## How the patch works

### What changes in the ROM

Two locations are patched — 17 bytes total:

| Location | Field | Before | After |
|----------|-------|--------|-------|
| Move data table, slot 15 | Effect | `0x00` (normal hit) | `0x2B` (high crit) |
| | Power | `50` | `200` |
| | Type | `0x00` (Normal) | `0x06` (Bug) |
| | Accuracy | `95` | `100` |
| | PP | `30` | `15` |
| Move name table, slot 15 | Name | `CUT` | `BUG SPLITTER` |

Flags, target, priority, and padding are unchanged.

### Why the overworld still works

HM field effects in Gen 3 are engine-hardcoded to a specific **move ID**, not to the move's name, type, or stats. The tree-cutting routine checks:

> "Does any party Pokémon have move #15 in its moveset?"

Replacing Cut's data at slot 15 does not change the slot number. A Pokémon that knows Bug Splitter has move #15, so the check passes and the animation plays.

### Move name encoding

Pokémon Gen 3 uses a custom character set. Each name is stored as a fixed 13-byte slot (12 characters + `0xFF` terminator). `BUG SPLITTER` is exactly 12 characters, filling the slot perfectly:

```
BC CF C1 00 CD CA C6 C3 CE CE BF CC FF
B  U  G  _  S  P  L  I  T  T  E  R  ∎
```

---

## Building from the pokeemerald source (advanced)

`build.py` provides an alternative pipeline for building Bug Splitter from scratch against a **clean Pokémon Emerald US ROM** using the [pokeemerald](https://github.com/pret/pokeemerald) decompilation project. This approach adds Bug Splitter as a proper new move (ID 355) and TM51 rather than replacing an existing move, but requires a full ARM cross-compiler toolchain.

<details>
<summary>Show pokeemerald build instructions</summary>

### Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.8+ | Runs the build and patch scripts |
| git | Clones the pokeemerald repository |
| devkitARM | ARM cross-compiler — [install guide](https://devkitpro.org/wiki/Getting_Started) |
| flips *(optional)* | IPS/BPS generation — [download](https://github.com/Alcaro/Flips/releases); a Python fallback is built in |

### Build

```bash
# Install devkitPro / devkitARM (Linux)
sudo dkp-pacman -S gba-dev
export DEVKITPRO=/opt/devkitpro
export DEVKITARM=$DEVKITPRO/devkitARM

# Run against a clean US Emerald ROM
python3 build.py --rom /path/to/emerald.gba
# Output: bug_splitter.ips
```

```
python3 build.py --rom FILE [options]

  --rom FILE       Path to clean Pokémon Emerald US ROM  (required)
  --output FILE    Output IPS filename  (default: bug_splitter.ips)
  --skip-clone     Use existing pokeemerald/ directory
  --skip-patch     Skip source edits (re-use previously patched source)
  --skip-build     Skip make step (use existing pokeemerald/pokeemerald.gba)
```

### Source files modified

| File | Change |
|------|--------|
| `include/constants/moves.h` | Add `MOVE_BUG_SPLITTER = 355`, bump `MOVES_COUNT` to 356 |
| `src/data/battle_moves.h` | Append Bug Splitter entry to `gBattleMoves[]` |
| *(move names file)* | Append `[MOVE_BUG_SPLITTER] = _("Bug Splitter")` |
| `include/constants/items.h` | Add `ITEM_TM51`, shift `ITEM_HM01–HM08` up by 1, bump `NUM_TECHNICAL_MACHINES` to 51 |
| *(items data file)* | Append TM51 item entry (price 1000, pocket TM/HM) |
| `src/pokemon.c` | Append `MOVE_BUG_SPLITTER` to `gTMHMMoves[]` as TM51 |
| `src/data/pokemon/tmhm_learnsets.h` | Set TM51 compatibility for all 36 Bug-type Pokémon |
| *(shop data)* | Add `ITEM_TM51` to Lilycove Dept Store and other TM-selling marts |

pokeemerald stores TM/HM compatibility as a 64-bit bitmask per species (bits 0–49 = TM01–50, bits 50–57 = HM01–08). Incrementing `NUM_TECHNICAL_MACHINES` from 50 to 51 shifts all HM bit positions automatically at compile time — no manual bitmask editing required.

### Troubleshooting

**`arm-none-eabi-gcc: command not found`**  
Install devkitARM and set `DEVKITPRO`/`DEVKITARM`. See the [devkitPro guide](https://devkitpro.org/wiki/Getting_Started).

**`patch_shops.py` cannot find shop data**  
Shop inventory location varies across pokeemerald versions. Manually add `ITEM_TM51` before the `ITEM_NONE` sentinel in the Lilycove Dept Store item array, then re-run with `--skip-clone --skip-patch`.

**Wrong move name or garbled text after teaching**  
The move name file was not auto-detected. Find `gMoveNames` in the pokeemerald source tree and append `[MOVE_BUG_SPLITTER] = _("Bug Splitter"),` manually.

</details>

---

## Project structure

```
bug-splitter/
├── scripts/
│   ├── patch_rom_direct.py   # Direct binary patcher (recommended)
│   ├── patch_moves.py        # pokeemerald: move data + name
│   ├── patch_items.py        # pokeemerald: TM51 item + gTMHMMoves[]
│   ├── patch_learnsets.py    # pokeemerald: TM51 learnset for Bug Pokémon
│   └── patch_shops.py        # pokeemerald: shop inventory
└── build.py                  # pokeemerald pipeline orchestrator
```
