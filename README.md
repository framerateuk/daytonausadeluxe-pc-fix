# Daytona USA Deluxe (PC, 1997) on modern PCs and the Steam Deck

## Why this exists

Played hours and hours of this over my friend's house on his Saturn as kids. The intro was probably
a subliminal introduction to heavy metal, and the split screen mode was brilliant. I know the original
is held as being a better game, but CCE/Deluxe is the game I always remember.

## What this does

Turns **your own** Daytona USA Deluxe PC CD (the PC version of the Saturn's Championship Circuit
Edition), plus Sega's official **Direct3D patch** if you have it, into a folder that runs on the
Steam Deck (Proton) or on Windows 10/11, with no installer and no registry entries:

- **Both renderers**: the patch's Direct3D exe (hardware 3D through dgVoodoo2, rendered at your
  screen's height instead of 640x480) and the disc's original software renderer (the 1997 look, and
  the bonnet view that the Direct3D patch removed). They share settings and records.
- **Copied straight from the CD**: what the installer copied, so no CD is needed.
- **Settings and records in `DAYTONA.INI`** beside the exe instead of the registry, so they travel
  with the folder and survive Steam's Exit Game.
- **CD soundtrack** from OGG files ripped from your disc, with fixes so the music keeps looping and
  doesn't go silent after a change of track, and each track cut so the game's track starts land
  exactly.
- **No dialogs a pad can't answer**: the Direct3D exe's driver dialog at every start and the
  "Exit game ?" question are gone.
- **Exact 30 / 60 frames a second** without a busy wait (the original ran 2% slow and kept a CPU
  core at 100%).
- **Gamepad on Windows**: an Xbox pad through XInput with analogue steering, the D-pad, both
  triggers and a sensible default layout. On the Steam Deck the game reads keys through a Steam
  Input layout instead (see below).
- **Fog off by default** in the Direct3D exe: the patch added fog that the software renderer and
  the Saturn never had. Settings > D3D Options turns it back on.
- **A Windows-only crash fixed**: the Direct3D exe closed straight after starting on Windows 10/11
  (it read memory it never cleared).

**No game files are in this repository.** Everything from the game comes from your disc and the
patch when you run `build.py`.

## What you need

| | |
|---|---|
| The game | The **Daytona USA Deluxe PC CD** (Sega, 1997, English; `GAME\DAYTONA USA Deluxe.exe` of 11 September 1997, "ver.1.08E") as `.cue` + `.bin` or CloneCD `.ccd` + `.img`, with its 23 audio tracks. `build.py` checks the exe and stops on another version. |
| The Direct3D patch (optional) | Sega's **"Daytona USA Deluxe - Direct 3D Patch"**, `ddx_d3d.exe` (640,932 bytes, "ver.1.20E", January 1998). Sega's site is long gone; game patch archives still have it. Without it you get the software renderer only. |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases) (tested with v2025.01.16). Keep the zip as downloaded. |

## Build

```
python3 build.py DaytonaUSADeluxe.cue --d3d-patch ddx_d3d.exe --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `DaytonaUSADeluxe/` with `game/` and `daytonadx_launch.sh` (for the Steam Deck), in under a
minute. The same `game/` folder runs on Windows; `--windows` leaves out the launch script. `--out DIR`
puts the result somewhere else. The original exes are kept in `game/_spare/`.

## Play on the Steam Deck

1. Copy `DaytonaUSADeluxe/` to the Deck, for example to `/home/deck/Games/DaytonaUSADeluxe/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse >
   `.../DaytonaUSADeluxe/game/DAYTONA USA Deluxe.exe`. Rename the shortcut "Daytona USA Deluxe".
   For the software renderer add `DAYTONA USA Deluxe SW.exe` too, as "Daytona USA Deluxe (Software)".
3. Properties > Compatibility: force **Proton 9.0** for each. Pin it rather than floating on
   Experimental.
4. Properties > Launch Options, for each:
   ```
   /home/deck/Games/DaytonaUSADeluxe/daytonadx_launch.sh %command%
   ```
5. Controller layout: in the game's controller settings start from a blank layout and set the
   buttons to these keys:

   | Deck | Key | Does |
   |---|---|---|
   | A, right trigger | X | accelerate; choose in menus |
   | X, left trigger | Z | brake; back in menus |
   | B / Y | Up arrow / Down arrow | shift up / down (manual gearbox) |
   | LB, RB | C | change view |
   | D-pad | arrow keys | steer (full lock), menus |
   | left stick, left / right only | Left / Right arrow | steer |
   | Start (Menu, right) | Enter | start, pause, choose |
   | Select (View, left) | Esc | back |

   Leave the left stick's up / down unbound: in a race Up / Down shift gear. The game reads the pad
   itself only on Windows. Under Wine its pad reads stall at random moments in this game (in every
   API: DirectInput, winmm, XInput), so on the Deck it reads keys only.

## Play on Windows

Run `game/DAYTONA USA Deluxe.exe` (Direct3D) or `game/DAYTONA USA Deluxe SW.exe` (software). For
the software exe, copy `game/dgVoodooSW.conf` over `game/dgVoodoo.conf` first (and
`dgVoodooD3D.conf` back for the Direct3D one); the Deck's launch script does this by itself. The
game's own window shows for a moment at start, with its menu bar and not answering yet, until the
intro switches to full screen.

If Windows asks to install DirectPlay at the first start, accept: the exe needs it (for its Link Game
network play) just to start.

## Controls

On Windows, an Xbox pad and the keyboard work at the same time:

| Pad (Windows) | Does | Keyboard |
|---|---|---|
| Left stick (analogue) or D-pad (full lock) | steer | Left / Right |
| RT or A | accelerate; choose in menus | X |
| LT or B | brake; back in menus | Z |
| Y / X | shift up / down (manual gearbox) | Up / Down |
| LB or RB | change view | C |
| Menu | start, pause | Enter |
| | back | Esc |
| | quit | Alt+F4 (no question) |

Holding both triggers cancels out, since they share one axis: use A with LT, or A and B. Other pads
go through the Windows joystick API; their buttons may need setting in the game's Joystick Settings
(F6). The keyboard gas key also chooses and the brake key also goes back in the menus, as A and B do.
Choose Automatic or Manual before each race; the gear keys do nothing with Automatic.

## Settings

`game/DAYTONA.INI` holds every setting and record; the game writes it at the title, at the mode
select and when you quit. Delete it to go back to the defaults (the records go too).

- Fog (Direct3D exe): Settings > D3D Options in the game.
- 3D resolution (Direct3D exe): `[DirectX] Resolution` in `game/dgVoodooD3D.conf`: `max` (the
  kit's: the largest 4:3 size the screen holds), `unforced` (the original 640x480) or `2x`.
- Smoothing: `Resampling = bilinear` (the kit's) or `pointsampled` (sharp pixels) in the
  dgVoodoo `.conf` files.
- Pad: add `[Retrodeck]` and `Pad=0` to `DAYTONA.INI` to turn the pad off on Windows (keyboard only),
  `Pad=1` to try it under Wine anyway.
- Music level: `CDDAVolume` in `game/winmm.ini`.
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  DirectDraw / Direct3D instead of dgVoodoo (640x480, no upscaling).

## Troubleshooting

- *"Please insert the DAYTONA USA Deluxe CD-ROM"*: you're running an unpatched exe from `_spare/`.
- *Black screen or a DirectDraw / Direct3D error*: `ddraw.dll`, `D3DImm.dll` and `dgVoodoo.conf`
  must sit beside the exe. Without dgVoodoo, Windows 10/11 offer no 16-bit 640x480 mode and the game
  stops with "ERR_NORESOLUTION".
- *No music*: `game/Music/Track02.ogg` must exist beside `winmm.dll`; on the Deck `launch.log` must
  show `WINEDLLOVERRIDES=winmm=n,b;...` (no log: the launch option is missing `%command%`).
- *The race runs at 30 frames a second*: that's the game (and the Saturn original).
- *F1 (help) does nothing*: Windows 10/11 no longer include WinHelp.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.
- *No bonnet (hood) view in the Direct3D exe*: Sega's patch removed it; the software exe has it.

Tested: both exes on the Steam Deck (Proton 9.0) and on Windows 11, built with the Direct3D patch.
A build without the patch (software exe with the disc's own `Resource.dll` and `dpctrl.dll`) is
how Sega shipped it but hasn't been played through.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files and the patch's, patches both exes, rips and pads the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained, with the new code's bytes; also runs on its own on either exe. |
| `caves.s`, `caves_d3d.inc`, `caves_sw.inc`, `build_caves.py` | The source of that new code (x86 assembly, both exes) and the script that assembles it with clang into `patch_exe.py`. Only needed to change a patch. |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 with Joliet names, and the audio tracks. |
| `config/` | dgVoodoo2's settings for each exe, and ogg-winmm's. |
| `steamdeck/daytonadx_launch.sh` | Proton launch wrapper: DLL overrides, the dgVoodoo settings for the exe being started. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Sega** made and published Daytona USA Deluxe and its Direct3D patch. Please own the game: this
  kit needs your disc.
- **Dege**: dgVoodoo2. **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, its patch, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
