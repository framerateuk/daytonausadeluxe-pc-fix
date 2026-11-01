# How it works

Notes on Daytona USA Deluxe (Sega PC, 1997; "DAY EVO" inside the exe, a new MSVC code base, not the
1996 Daytona USA port: only the CD player module is shared) and Sega's Direct3D patch. Two exes:

| | Direct3D exe (the patch's) | Software exe (the disc's) |
|---|---|---|
| File | `game\DAYTONA USA Deluxe.exe` in `ddx_d3d.exe` | `GAME\DAYTONA USA Deluxe.exe` on the CD |
| Size, MD5 | 1,096,704 bytes, `61a168d474f6bab8fdeffc3a1058082e` | 1,081,856 bytes, `c1e334a15d9472219441ed5f2bb89fb1` |
| Linked, About box | 23 December 1997, ver.1.20E | 11 September 1997, ver.1.08E |
| Renderer | Direct3D 5 immediate mode, HAL device | DirectDraw, drawn by the CPU |

Addresses below are virtual addresses in the Direct3D exe; `patch_exe.py` lists both exes' sites, and
the software exe's were found by matching the same code. The new code sits in a 7th section `.ddx` that
`patch_exe.py` adds (VA `0x8c1000`, software exe `0x8bf000`), assembled from `caves.s`.

## The disc and the patch

Track 1 is the data track (ISO 9660 with Joliet: the long, mixed-case names); tracks 2-24 are the music.
The installer's full install copies `GAME\` (with `Resource\`) to `C:\SEGA\DAYTONA USA Deluxe`, the
English help from `DOC\English`. The patch is a WinZip self-extractor; its `Setup.exe` copies `game\`
over the installed folder: the new exe, `RESOURCE.DLL` and `DPCTRL.dll` (supersets of the disc's, with
the Direct3D options dialogs) and nine time-of-day course pictures in `resource\640x480x16\mode\`.
`build.py` does the same, and the software exe runs from the same folder.

## Disc check (nocd)

At start-up `0x43ae30` looks for `X:\Game\DAYTONA USA Deluxe.exe` on every CD-ROM drive ("Please insert
the DAYTONA USA Deluxe CD-ROM"). It now returns 1. Nothing else needs the CD: every data file is looked up
by its bare relative name first and on the CD only if that fails, and CD audio opens the plain `cdaudio`
device.

## Settings and records: registry -> DAYTONA.INI (profile, seqsave)

Everything went to `HKCU\Software\SEGA\DAYTONA USA Deluxe\Profile\<section>` through four helpers
(write string / binary, read string / binary: `0x418cc1`, `0x418da4`, `0x418e80`, `0x418f57`). Each now
uses `Write/GetPrivateProfileString/StructA` on `.\DAYTONA.INI`, same sections and keys: `[Memory]` (the
options, layouts and car setups block, the records), `[JoystickSettings]`, `[KeyboardSettings]`,
`[D3DOPTIONS]`, `[System]`, `[Hidden]`. Both exes use the same blocks, so they share one file.

The game saved only on a normal quit; a process ended from outside (Steam's Exit Game) wrote nothing.
`seqsave` also saves whenever the title or the mode select is entered.

## CD audio (cdnotify, cdplay) and the track lengths

The CD module plays track N "from the position of track N to the position of track N+1" in MSF, with
notify while CD Loop is on. Two places relied on Windows' `MCI_NOTIFY_ABORTED` after a stop, which
ogg-winmm never sends: each stop counted one notification to swallow, so after a change of track the
next natural end was swallowed and the music stopped instead of looping (`cdnotify`: the counting
becomes nop); and a deferred play that found the drive still playing stopped it and waited for that
notification to start the new track: silence (`cdplay`: always the normal play path).

ogg-winmm keeps track starts in whole milliseconds and rounds MSF down both ways, so a start that is not a
multiple of 40 ms lands in the previous track. `build.py` trims up to 2 s of digital silence from each
track's end and pads it to 1764k + 1 samples (exactly k * 40 ms).

## Frame pacing (pace)

The main loop never waits for messages; every turn it asks `0x448c9f(ticks per second)` whether to run a
logic tick and a drawing: 60 per second in the menus, 30 in the race (as the Saturn's Championship Circuit
Edition). The original ran a tick once `now - last >= 1000 / R` whole milliseconds had passed (34 ms: 29.4
Hz, 2 % slow) and returned at once otherwise, so one core spun at 100 %. `pace`: tick k is due at
`T0 + k * 1000 / R` ms; until then it sleeps (to 2 ms before the tick); a tick a whole period late runs
without drawing (at most 3 in a row); 125 ms late, a new rate or the game's own reset restarts the
schedule. `timeBeginPeriod(1)` once.

## Graphics (autook, ddguid, fogoff, heapzero)

The Direct3D exe uses `IDirectDraw2`, `IDirect3D2` and always the HAL device, 640x480 or 320x240 in
16-bit colour (its display mode callback enables only those). dgVoodoo2 2.79.3 (`ddraw.dll` +
`D3DImm.dll`) runs it on Direct3D 11, full screen, 4:3, the 3D rendered at the largest 4:3 size the
screen holds (`[DirectX] Resolution = max`). The software exe gets the same dgVoodoo with the resolution
unforced: its 640x480 picture is scaled to the screen.

- `autook`: before every start a modal "Direct3D" dialog (Japanese only) listed the DirectDraw drivers
  and waited for OK. Its `WM_INITDIALOG` now selects the first driver with 3D (else the first) and runs
  the OK handler, so it never appears.
- `ddguid`: the primary driver was created through a pointer to an all-zero GUID; it now passes NULL,
  the documented "active display driver".
- `fogoff`: the D3D Options default `FogEnabled` 1 -> 0 (the software renderer and the Saturn have no
  such fog). The in-game D3D Options dialog still turns it on.
- `heapzero` (Windows): the texture table set-up (`0x41ddae`) allocates 0x200 entries with `HeapAlloc`
  and at once calls the reset `0x41dc14`, which Releases every entry marked in use through its COM
  interfaces and only then clears the table. Under Wine a fresh heap block is zeros, so nothing is
  released. On Windows 10/11 the heap hands back used memory, and the game called `Release` on junk (an
  access violation at `0x41dccd`), which its own exception handler turned into a silent
  `DestroyWindow` + `ExitProcess` just after start: no message, no Windows Error Reporting entry. The
  game's allocator (`0x444770`) now passes `HEAP_ZERO_MEMORY`.

The Direct3D exe has no bonnet view: Sega removed its loader, not just the menu entry. The software exe
has all four views. `mode16` (software exe): the default display mode 640x480 8-bit (palettised, which
a modern 32-bit desktop can't supply) -> 640x480 16-bit.

## Exit (noconfirm)

Alt+F4 and the menu's Exit Game opened an "Exit game ?" Yes / No dialog, which a pad can't answer over a
full-screen game. `noconfirm` takes the Yes branch at once (everything is saved, then the window goes).

## Controls (pad, paddef, defaults, joyev, gassel)

The game reads up to 16 joysticks through DirectInput and posts each one's state as an event; layouts map
16 functions (Gas, Brake, Shift Up / Down, Gears 1-4, View Change, Up / Down / Left / Right, Select,
Cancel, Start) to buttons or axis directions. It knows eleven 1997 pads by name; anything else got a
default with gears on the stick, no Start button and nothing on the triggers or the POV hat.

- `pad`: after each read, button 29 = A or right trigger, 30 = B or left trigger, 31 = LB or RB (the
  triggers share the Z axis, as Windows' DirectInput view of an Xbox pad has them), a 6 % dead zone on
  X, and the D-pad pushes the stick to full lock in 8 directions.
- `paddef`: the default layout for an unknown pad: Gas 29, Brake 30, Shift Up Y, Shift Down X, View 31,
  Select A, Cancel B, Start Menu. `defaults`: analogue steering on, high-polygon mode on.
- `joyev`: the race reads only player 1, which was DirectInput device 0; the first device on which a
  button is pressed now becomes player 1.
- `gassel`: the keyboard's gas key also selects and the brake key also goes back in the menus.

## The pad under Wine (joyread, nojoy, noacq, coop, noff, digital)

On the Steam Deck the controls of both exes froze at random moments (intro, menus, minutes into a race).
Wine's reader for the pad, inside the game's process, stops delivering reports for good while Linux
still gets the pad's events; DirectInput, the winmm joystick API (built on the same reader) and XInput
all failed this way, in this game only. The keyboard never failed. So the exe now decides once, at
start, whether to read the pad:

- off when `ntdll.dll` exports `wine_get_version` (Proton), on under Windows; `[Retrodeck] Pad=1` / `Pad=0`
  in `DAYTONA.INI` overrides either way;
- `nojoy`: off, no joystick device is created at all (no Wine reader); `digital`: the keyboard's steering
  curve, whatever the analogue options say;
- `joyread`: on, the pad is read through XInput (`xinput1_4` / `1_3` / `9_1_0`), else winmm
  `joyGetPosEx`, and the result is written into the game's DirectInput state, then `pad` as above;
- `noacq`, `coop`, `noff`: the joystick is never acquired, opened non-exclusive, never treated as
  force feedback (a failing force-feedback call would end the game).

On the Deck a Steam Input layout sends the game's keys (X gas, Z brake, Up / Down gears, C view, arrows,
Enter, Esc).
