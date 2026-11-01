#!/usr/bin/env python3
"""Patch Daytona USA Deluxe's exe in place: the "DAYTONA USA Deluxe.exe" of Sega's official Direct3D patch
(ddx_d3d.exe, game\\, 1,096,704 bytes, MD5 61a168d474f6bab8fdeffc3a1058082e, linked 23 Dec 1997, "ver.1.20E"),
not the disc's software-rendered exe of 11 Sep 1997.

  patch_exe.py "game/DAYTONA USA Deluxe.exe"         the Direct3D exe (the patch's)
  patch_exe.py "game/DAYTONA USA Deluxe SW.exe"      the software exe (the disc's, 1,081,856 bytes,
                                                     MD5 c1e334a15d9472219441ed5f2bb89fb1, 11 Sep 1997, ver.1.08E)

The exe is recognised by its size. The software exe gets the same patches at its own addresses (found by
matching the code; caves_sw.inc, docs/TECHNICAL.md) except autook and ddguid (no driver dialog), plus mode16. The
addresses below are the Direct3D exe's.

Applies every patch not yet applied and reports each; refuses (writes nothing) on unexpected bytes.
docs/TECHNICAL.md has more on each one. The new code is in caves.s (build_caves.py
assembles it and checks CAVE / LABELS below).

  section   a 7th section ".ddx" for the new code (header in the free space at 0x268, NumberOfSections 6 -> 7,
            SizeOfImage 0x4c1000 -> 0x4c2000): VA 0x8c1000, 0x1000 bytes read/write/execute, raw data (CAVE)
            appended at the old end of the file, 0x10bc00. Variables at 0x8c1f00 (zero at load).
  nocd      0x43ae30 (start-up 0x44aa56: GetModuleFileNameA, then 0x43273d looks for "X:\\Game\\DAYTONA USA
            Deluxe.exe" on every DRIVE_CDROM; none: "Please insert the DAYTONA USA Deluxe CD-ROM" OK/Cancel)
            returns 1. Nothing else needs the CD: every file is found through 0x43273d, which tries the bare
            relative name in the working directory first and the CD's Game\\ only when that fails; CD audio
            opens the plain "cdaudio" device (drive -1, 0x4bf100).
  profile   every setting and record went to the registry, HKCU\\Software\\SEGA\\DAYTONA USA Deluxe\\Profile\\
            <section> (JoystickSettings, KeyboardSettings, Memory = records + the DAYTONA_PROTECTED_OBJECT
            options block, D3DOPTIONS, System, Hidden), through four helpers: 0x418cc1 WriteString,
            0x418da4 WriteBinary, 0x418e80 ReadString, 0x418f57 ReadBinary. Each now jumps to a cave using
            Get/WritePrivateProfileString/StructA on ".\\DAYTONA.INI" (same section and key names), so the
            settings live beside the exe and travel with the folder. The game writes its own defaults on the
            first run; nothing has to be imported.
  cdnotify  the CD player (0x4250a7.. "cd_play()", "CD repeat", same module as Daytona USA 1996) counted the
            MCI_NOTIFY_ABORTED it expected after each MCI_STOP of a playing track (0x425862 before every
            new track, 0x425456 at exit: inc [0x4bf108]) and swallowed that many notifications in the
            MM_MCINOTIFY handler 0x425a44. ogg-winmm notifies only a natural end, so after any change of
            track the next end was swallowed: no loop. Both incs become nop.
  cdplay    _CDPlay (0x425afc, one main-loop turn after cd_play) that still found the drive playing sent
            MCI_STOP and left the new track to the abort notification (flag 4): silence under ogg-winmm,
            whose stop returns before its thread marks the drive stopped. 0x425b95 jne -> jmp: always the
            normal play path 0x425bbf (ogg-winmm stops the old track itself; flag 4 is not set, so the
            track is not replayed at its end either).
  pace      the frame pacer 0x448c9f (from the idle routine 0x4552a0, ticks per second 60 in the menus and 30
            in the race, table 0x422a2d by sequence) let a tick run when a whole period had passed since the
            last one, in whole milliseconds (34 ms: 29.4 Hz instead of 30; 17 ms: 58.8 instead of 60), and
            otherwise returned at once to a PeekMessage loop that called it again: one core flat out.
            0x448cb4 jumps to PACE: tick k due at T0 + k * 1000 / R ms (exactly 30 / 60 Hz), Sleep until
            2 ms before the tick, a tick a period late runs without drawing (at most 3 in a row), 125 ms
            late restarts the schedule; timeBeginPeriod(1) once. Then the original statistics (0x449141).
  pad       the DirectInput joystick poll (0x45f166, per frame, 16 devices) jumps after GetDeviceState
            (0x45f1fc) to PAD: buttons 29 / 30 / 31 = A or right trigger / B or left trigger / LB or RB
            (the triggers share the Z axis: right low, left high, as Proton and Windows' Xbox driver report
            them), a 6 % dead zone on X, and the D-pad (POV hat, never read by the game) pushes X / Y to
            full lock in 8 directions.
  paddef    the default layout for a joystick the game does not know by name (table 0x4d5a48 entry 11,
            0x441234: gears on stick up / down, view on X, no Start button at all) -> PADDEF: Gas 29, Brake 30,
            Shift Up Y, Shift Down X, View Change 31, Up / Down / Left / Right the stick and D-pad, Select A,
            Cancel B, Start Menu.
  defaults  the DAYTONA_PROTECTED_OBJECT defaults (0x40d4fc, used while DAYTONA.INI has none): "Analog Steering
            Control" on for both players (DEFS, from the call at 0x40d5ca; it matters only in pad mode, see
            digital), and High-polygon Mode on (0x89cee8 = 3 -> 0xb).
  autook    the D3D patch opens a "Direct3D" driver dialog (0x8a, Japanese only) at every start
            (0x44a135 from 0x46967e) and waits for OK. Its WM_INITDIALOG end (0x449e87) jumps to AUTOOK:
            the first driver with DDCAPS_3D (else the first) is selected and the OK handler 0x449d6a runs
            (item -> 0x4bf230, EndDialog): no dialog.
  ddguid    the chosen driver's DirectDrawCreate (0x469689 -> 0x45764e) passed a pointer to an all-zero GUID
            for the primary display driver; it now passes NULL for it (DDGUID), the documented "active
            display driver" that dgVoodoo2 and Wine take without question.
  noconfirm WM_CLOSE (Alt+F4, menu Exit Game, the title's EXIT) opened the "Exit game ?" Yes / No dialog
            (0x40cd10), which a pad cannot answer over a full-screen game; 0x40cd35 jne -> jmp: as if Yes
            (settings saved by 0x4325e4, DestroyWindow).
  joyev     the event 0x12 handler 0x4218ce mapped DirectInput device n to player n (n < 2). The menus take
            input from any player, the race only from player 1 (0x421a25, 0x41763a), so a pad that is not
            device 0 worked in the menus and was dead in the race (seen on the Steam Deck). 0x4218ce now
            jumps to JOYEV: the first device whose buttons 1-28 are pressed becomes player 1 for the session
            and device 0 takes its place; layout and record of that player as before (mapper 0x4416b1).
  seqsave   the sequence change 0x45a87c (0x45a8af) jumps to SEQSAVE: entering the title (3) or the mode select
            (4) also saves everything as the exit does (0x40cfd0(1) -> DAYTONA.INI), because Steam's Exit Game
            ends the process without WM_CLOSE (no DAYTONA.INI afterwards).
  fogoff    (Direct3D exe) the D3D Options default FogEnabled (0x40d680, used while DAYTONA.INI has no
            [D3DOPTIONS] FogEnabled) 1 -> 0: D3DRENDERSTATE_FOGENABLE (0x425d98) off, as the software renderer
            and the Saturn never had that fog. The D3D Options dialog still turns it on.
  heapzero  (Direct3D exe) the game's allocator 0x444770 (HeapAlloc(GetProcessHeap(), 0, size)) now passes
            HEAP_ZERO_MEMORY (0x444786 push 0 -> push 8). The texture table set-up 0x41ddae allocates its 0x200
            entries (0x12800 bytes, [0x4bd3b0]) and at once calls the reset 0x41dc14, which Releases every entry
            marked in use (+0xc) through its interfaces (+8, +4) BEFORE its memset clears the table: harmless
            while the new block is zeros (Wine, the Steam Deck), but on Windows the heap hands back used memory
            and the game called Release on a junk pointer (vtable 1: access violation at 0x41dccd, read of
            0x00000009), which its own handler turned into a silent DestroyWindow + ExitProcess right after the
            640x480 16-bit mode was picked: "closes instantly" (Windows 11 24H2; found with a logging
            build). Every allocation zeroed is what Wine already gives the game.
  coop      the joystick's cooperative level (0x45edc2, SetCooperativeLevel in 0x45ecea) 9 = DISCL_EXCLUSIVE |
            DISCL_BACKGROUND -> 0xa = DISCL_NONEXCLUSIVE | DISCL_BACKGROUND (exclusive access is only needed for
            force feedback). Kept with noff (tried while Wine's dinput HID reader stalled at random moments);
            harmless now that the device is never acquired (noacq / joyread).
  noff      the pad is never treated as a force-feedback device: the enumeration's DIDC_FORCEFEEDBACK test
            (0x45ec76: autocentre property + effect creation 0x45ecc7) and the two run-time tests (0x441c93:
            SendForceFeedbackCommand(STOPALL); 0x441cf7: effect stop pass) and the "is FF" helper 0x43cac8
            (0x43cb0d) all take the no-FF branch. A failing FF call would end the game through 0x420ea8.
  gassel    the keyboard mapper 0x441a97 (per tick, 0x421981) stores its slot mask at 0x441af7; it now jumps to
            KSEL, which also sets Select (bit 13) while Gas (bit 0) is down and Cancel (bit 14) while Brake
            (bit 1) is down: the gas key (X, the Deck's A / right trigger through Steam Input) selects and the
            brake key (Z, the Deck's X / left trigger) goes back in the menus, as Enter and Esc do. In a race only
            the pause screen reads them (new presses only): Select picks the item (0x4176ba), Cancel resumes the
            race (0x41771c). The pad path is unchanged (its A / B are already Gas + Select / Brake + Cancel).
  joyread   the joystick poll 0x45f166 (0x45f1b5, Poll + GetDeviceState) jumps to JOYREAD. Pad mode (PADMODE,
            decided once: .\DAYTONA.INI [Retrodeck] Pad=1 / Pad=0 if present, else off under Wine - ntdll exports
            wine_get_version - and on under Windows): XInputGetState(0) (xinput1_3 / 1_4 / 9_1_0) fills the
            game's DIJOYSTATE as Proton's DInput view of the pad looked, else (no XInput, or it never answered)
            winmm joyGetPosEx(0); then PAD. Pad mode off: unplugged. Under Wine (the Steam Deck) the reads of the
            pad failed at random moments in this game's process through DirectInput (builds 1-4), winmm (5) and
            XInput alike, so there the pad reaches the game as keys through Steam Input (docs/TECHNICAL.md).
  nojoy     the DirectInput set-up 0x45eb80 calls the joystick enumeration (0x45ecea at 0x45ebf9: EnumDevices +
            CreateDevice + data format + cooperative level) only in pad mode (NOJOY); off, the 16 device slots
            0x864c24 stay empty and the poll, the layout load / save and the force-feedback code skip them. The
            keyboard device is created as before.
  digital   the race set-up 0x4232b0 and the steering curve choice 0x466792 read the player's "Analog Steering /
            Gas/Brake Control" options; out of pad mode they always take the digital branch (DIG1-3 at 0x4232d4,
            0x4232e5, 0x4667af): the Saturn pad's curve 0x4e5cb8 for the keys, whatever DAYTONA.INI says.
  noacq     the joystick enumeration 0x45eb80 acquired each device (0x45ec3f..0x45ec4a, Acquire); now never, so
            Wine starts no DirectInput reader for the pad (the software exe has no such call). The keyboard stays
            DirectInput.
  mode16    (software exe) [System] DisplayMode default (0x418ca2) 2 (640x480 8-bit, palettised) -> 3 (640x480
            16-bit): no 8-bit palette under Wine / modern desktops, and the 16-bit bitmap set.
"""
import os, struct, sys

def rel32(src, dst):                   # e8/e9 at src (5 bytes) -> dst
    return (dst - (src + 5)).to_bytes(4, "little", signed=True)

def jmp(src, dst): return b"\xe9" + rel32(src, dst)
def call(src, dst): return b"\xe8" + rel32(src, dst)

# caves.s assembled after caves_d3d.inc / caves_sw.inc (build_caves.py --write keeps these in step with caves.s)
CAVE_D3D = bytes.fromhex(
    "68a0188c00ff15f8f5890085c0740bff74240450ff1528f68900c204008b048d201f8c0085c0751751ff348d90188c00"
    "e8cbffffff5989048d201f8c0085c0c331c9e8d6ffffff741368b7188c00ff742410ff742410ff742410ffd0f7d819c0"
    "f7d8c3b901000000e8b0ffffff741768b7188c00ff742414ff742414ff742414ff742414ffd0f7d819c0f7d8c3b90200"
    "0000e886ffffff741b68b7188c00ff742418ff742418ff742418ff742418ff742418ffd0c3b903000000e85effffff74"
    "1768b7188c00ff742414ff742414ff742414ff742414ffd0f7d819c0f7d8c3c705001f8c000100000068c5188c00e80d"
    "ffffffa3041f8c0068ad188c00ff15f8f5890085c0741468cb188c0050ff1528f6890085c074046a01ffd0c3a10c1f8c"
    "004069c0e803000031d2f7f10305081f8c00c3833d001f8c00007505e89effffff8b4d0885c97505b93c000000833dbc"
    "e35000000f85d20000003b0d101f8c000f85c6000000e8b1ffffff8b55fc29c20f888000000083fa7d0f8dad000000ff"
    "050c1f8c0089c86bc03c39050c1f8c00721029050c1f8c008105081f8c0060ea0000e875ffffff8b55fc29c27828833d"
    "141f8c0003731fff05141f8c00c705c0e3500000000000c705c4e3500001000000e996000000c705141f8c0000000000"
    "c705c0e3500001000000c705c4e3500001000000eb76c705c0e3500000000000c705c4e3500000000000f7da83fa0372"
    "5b83ea0283fa147605ba14000000a1041f8c0085c0744552ffd0eb40890d101f8c008b45fca3081f8c00c7050c1f8c00"
    "00000000c705141f8c0000000000c705bce3500000000000c705c0e3500001000000c705c4e35000010000008b45fca3"
    "88e35000e9c87eb8ff0fb6051d1f8c00803d1c1f8c00007564c6051c1f8c00016843198c00e866fdffff85c0742268b7"
    "188c006aff6863198c006859198c00ffd083f8ff740a85c00f95c00fb6c0eb286867198c00ff15f8f5890085c0741468"
    "71198c0050ff1528f6890085c0740431c0eb05b801000000a21d1f8c00c3e886ffffff85c07405e9eed9b9ffc30f84db"
    "1fb6ffe871ffffff85c00f84ce1fb6ffe9c51fb6ff0f84d41fb6ffe859ffffff85c00f84c71fb6ffe9be1fb6ff0f8496"
    "54baffe841ffffff85c00f848954baffe97054baffc745f0ffffffff837dfc000f8550dfb9ffe81effffff85c00f8443"
    "dfb9ff565783ec34803d1a1f8c00007505e8bf010000a1301f8c0085c00f84e300000089e1516a00ffd085c07412803d"
    "1b1f8c00000f8590010000e9c6000000c6051b1f8c00018b7df40fbf442408c1f808e8c401000089070fbf44240ac1f8"
    "08f7d8e8b30100008947040fb64424060fb64c240729c8d1f8e89d0100008947080fbf44240cc1f808e88d0100008947"
    "0c0fbf44240ec1f808f7d8e87b01000089471031c089471489471889471c0fb744240483e00f8b048530188c00894720"
    "c74724ffffffffc74728ffffffffc7472cffffffff5783c73031c0b908000000f3ab5f0fb754240431c90fb7044d7018"
    "8c0085c27405c6440f30804183f90a72e9e9b7000000c7042434000000c7442404ff000000546a00ff1510f8890085c0"
    "0f85a50000008b7df48b442408e8f400000089078b44240ce8e90000008947048b442410e8dd0000008947088b442418"
    "e8d100000089470c8b44241ce8c50000008947108b442414e8b9000000894714c7471800000000c7471c000000000fb7"
    "4424283dffff0000750383c8ff894720c74724ffffffffc74728ffffffffc7472cffffffff8b54242031c931c0d1ea73"
    "02b08088440f304183f92072eec745f00000000083c4345f5eeb6d83c4345f5ee971ddb9ffc6051a1f8c00016882198c"
    "00ff1504f6890085c0751e6890198c00ff1504f6890085c0750f689e198c00ff1504f6890085c0741168ae198c0050ff"
    "1528f68900a3301f8c00c383f8817d05b881ffffffc325ffff000069c0ff000000c1e81083e87fc3837df0000f8c04dd"
    "b9ff538b4df48b410883f8e07c0c83f8207f07c605181f8c00018a5930803d181f8c0000740783f8d07f02b38088594c"
    "8a5931803d181f8c0000740783f8307c02b38088594d8a59340a593588594e8b0189c3c1fb1f31d829d883e8087f0431"
    "c0eb186bc07f51b97700000031d2f7f15983f87f7605b87f00000031d829d889018b41206683f8ff744b0fb7c03da08c"
    "0000734105ca08000051b99411000031d2f7f1590fb68084188c00a8017407c7410481ffffffa8027407c741047f0000"
    "00a8047406c70181ffffffa8087406c7017f0000005be98bdbb9ff8b45f8a80174050d00200000a80274050d00400000"
    "8b4d088901e96504b8ff578b7c240831c0b910000000f3ab5f8b442404c7001d000000c740041e000000c74008040000"
    "00c7400c03000000c740201f000000c7402423000000c7402824000000c7402c21000000c7403022000000c740340100"
    "0000c7403802000000c7403c08000000c356578b75fc6a006a00688b01000056ff1580f7890085c07e4089c75331db6a"
    "0053689901000056ff1580f7890083f8ff740583380075074339fb72e231db6a0053688601000056ff1580f78900ff75"
    "08e81486b8ff83c4045b5f5eb801000000e92b87b8ff833d38f24b000074076a00e91c7fbaff683cf24b00e9127fbaff"
    "8b4c240883f91073628b54240c803d191f8c0000751931c0807c02300075084083f81c72f3eb088d4101a2191f8c000f"
    "b605191f8c0085c0740f4839c1750431c9eb0685c9750289c183f902731d89c8c1e00605f8c8890050526bc1190568c7"
    "890050e8c9feb7ff83c40c31c0c38b450c3b0584668600a384668600741483f803740583f804750a6a01e8c1b7b4ff83"
    "c404e9a090b9ffc705f8cc890001000000c70510cd890001000000e99013b9ffffffffff0000000050460000ffffffff"
    "786900000c7b0000e4570000ffffffff2823000094110000bc340000ffffffffffffffffffffffffffffffffffffffff"
    "00100020004000800001000220001000400080000109080a02060405010f1f00db188c00f6188c0011198c002a198c00"
    "4b45524e454c33322e646c6c0057494e4d4d2e646c6c002e5c444159544f4e412e494e4900536c6565700074696d6542"
    "6567696e506572696f640057726974655072697661746550726f66696c65537472696e67410057726974655072697661"
    "746550726f66696c6553747275637441004765745072697661746550726f66696c65537472696e674100476574507269"
    "7661746550726f66696c6553747275637441004765745072697661746550726f66696c65496e744100526574726f6465"
    "636b00506164006e74646c6c2e646c6c0077696e655f6765745f76657273696f6e0078696e707574315f332e646c6c00"
    "78696e707574315f342e646c6c0078696e707574395f315f302e646c6c0058496e707574476574537461746500"
)
LABELS_D3D = {"KFN": 0x8c1000, "PROF": 0x8c101d, "P_WSTR": 0x8c1040, "P_WBIN": 0x8c1063, "P_RSTR": 0x8c108d, "P_RBIN": 0x8c10b5, "INIT": 0x8c10df, "DUE": 0x8c111c, "PACE": 0x8c1133, "P_DRAW": 0x8c11d6, "P_WAIT": 0x8c11f6, "P_RESYNC": 0x8c122c, "P_OUT": 0x8c126c, "PADMODE": 0x8c1279, "NOJOY": 0x8c12ee, "DIG1": 0x8c12fd, "DIG2": 0x8c1315, "DIG3": 0x8c132d, "JOYREAD": 0x8c1345, "J_XOK": 0x8c13a0, "J_WINMM": 0x8c1466, "J_OK": 0x8c151d, "J_FAIL": 0x8c152b, "XLOAD": 0x8c1535, "JCLAMP": 0x8c157b, "JAX": 0x8c1586, "PAD": 0x8c1598, "KSEL": 0x8c167b, "PADDEF": 0x8c169a, "AUTOOK": 0x8c1701, "DDGUID": 0x8c1766, "JOYEV": 0x8c1780, "SEQSAVE": 0x8c17ee, "DEFS": 0x8c1817, "XPOV": 0x8c1830, "XBTN": 0x8c1870, "POVTAB": 0x8c1884, "PNAMES": 0x8c1890, "s_kernel32": 0x8c18a0, "s_winmm": 0x8c18ad, "s_ini": 0x8c18b7, "n_sleep": 0x8c18c5, "n_tbp": 0x8c18cb, "n_wpps": 0x8c18db, "n_wpst": 0x8c18f6, "n_gpps": 0x8c1911, "n_gpst": 0x8c192a, "n_gppi": 0x8c1943, "s_retro": 0x8c1959, "s_padkey": 0x8c1963, "s_ntdll": 0x8c1967, "n_wgv": 0x8c1971, "s_xi13": 0x8c1982, "s_xi14": 0x8c1990, "s_xi910": 0x8c199e, "n_xgs": 0x8c19ae}
CAVE_SW = bytes.fromhex(
    "6820f88b00ff1588c5890085c0740bff74240450ff15c8c58900c204008b048d20ff8b0085c0751751ff348d10f88b00"
    "e8cbffffff5989048d20ff8b0085c0c331c9e8d6ffffff74136837f88b00ff742410ff742410ff742410ffd0f7d819c0"
    "f7d8c3b901000000e8b0ffffff74176837f88b00ff742414ff742414ff742414ff742414ffd0f7d819c0f7d8c3b90200"
    "0000e886ffffff741b6837f88b00ff742418ff742418ff742418ff742418ff742418ffd0c3b903000000e85effffff74"
    "176837f88b00ff742414ff742414ff742414ff742414ffd0f7d819c0f7d8c3c70500ff8b00010000006845f88b00e80d"
    "ffffffa304ff8b00682df88b00ff1588c5890085c07414684bf88b0050ff15c8c5890085c074046a01ffd0c3a10cff8b"
    "004069c0e803000031d2f7f1030508ff8b00c3833d00ff8b00007505e89effffff8b4d0885c97505b93c000000833d74"
    "235100000f85d20000003b0d10ff8b000f85c6000000e8b1ffffff8b55fc29c20f888000000083fa7d0f8dad000000ff"
    "050cff8b0089c86bc03c39050cff8b00721029050cff8b00810508ff8b0060ea0000e875ffffff8b55fc29c27828833d"
    "14ff8b0003731fff0514ff8b00c7057823510000000000c7057c23510001000000e996000000c70514ff8b0000000000"
    "c7057823510001000000c7057c23510001000000eb76c7057823510000000000c7057c23510000000000f7da83fa0372"
    "5b83ea0283fa147605ba14000000a104ff8b0085c0744552ffd0eb40890d10ff8b008b45fca308ff8b00c7050cff8b00"
    "00000000c70514ff8b0000000000c7057423510000000000c7057823510001000000c7057c235100010000008b45fca3"
    "40235100e9c834baff0fb6051dff8b00803d1cff8b00007564c6051cff8b000168c3f88b00e866fdffff85c074226837"
    "f88b006aff68e3f88b0068d9f88b00ffd083f8ff740a85c00f95c00fb6c0eb2868e7f88b00ff1588c5890085c0741468"
    "f1f88b0050ff15c8c5890085c0740431c0eb05b801000000a21dff8b00c3e886ffffff85c07405e92ce5b7ffc30f8438"
    "39b4ffe871ffffff85c00f842b39b4ffe92239b4ff0f843139b4ffe859ffffff85c00f842439b4ffe91b39b4ff0f84e6"
    "20b7ffe841ffffff85c00f84d920b7ffe9c020b7ffc745f0ffffffff837dfc000f859aeab7ffe81effffff85c00f848d"
    "eab7ff565783ec34803d1aff8b00007505e8bf010000a130ff8b0085c00f84e300000089e1516a00ffd085c07412803d"
    "1bff8b00000f8590010000e9c6000000c6051bff8b00018b7df40fbf442408c1f808e8c401000089070fbf44240ac1f8"
    "08f7d8e8b30100008947040fb64424060fb64c240729c8d1f8e89d0100008947080fbf44240cc1f808e88d0100008947"
    "0c0fbf44240ec1f808f7d8e87b01000089471031c089471489471889471c0fb744240483e00f8b0485b1f78b00894720"
    "c74724ffffffffc74728ffffffffc7472cffffffff5783c73031c0b908000000f3ab5f0fb754240431c90fb7044df1f7"
    "8b0085c27405c6440f30804183f90a72e9e9b7000000c7042434000000c7442404ff000000546a00ff15e0c7890085c0"
    "0f85a50000008b7df48b442408e8f400000089078b44240ce8e90000008947048b442410e8dd0000008947088b442418"
    "e8d100000089470c8b44241ce8c50000008947108b442414e8b9000000894714c7471800000000c7471c000000000fb7"
    "4424283dffff0000750383c8ff894720c74724ffffffffc74728ffffffffc7472cffffffff8b54242031c931c0d1ea73"
    "02b08088440f304183f92072eec745f00000000083c4345f5eeb6d83c4345f5ee9bbe8b7ffc6051aff8b00016802f98b"
    "00ff15b0c5890085c0751e6810f98b00ff15b0c5890085c0750f681ef98b00ff15b0c5890085c07411682ef98b0050ff"
    "15c8c58900a330ff8b00c383f8817d05b881ffffffc325ffff000069c0ff000000c1e81083e87fc3837df0000f8c4ee8"
    "b7ff538b4df48b410883f8e07c0c83f8207f07c60518ff8b00018a5930803d18ff8b0000740783f8d07f02b38088594c"
    "8a5931803d18ff8b0000740783f8307c02b38088594d8a59340a593588594e8b0189c3c1fb1f31d829d883e8087f0431"
    "c0eb186bc07f51b97700000031d2f7f15983f87f7605b87f00000031d829d889018b41206683f8ff744b0fb7c03da08c"
    "0000734105ca08000051b99411000031d2f7f1590fb68005f88b00a8017407c7410481ffffffa8027407c741047f0000"
    "00a8047406c70181ffffffa8087406c7017f0000005be9d5e6b7ff8b45f8a80174050d00200000a80274050d00400000"
    "8b4d088901e965d5b5ff578b7c240831c0b910000000f3ab5f8b442404c7001d000000c740041e000000c74008040000"
    "00c7400c03000000c740201f000000c7402423000000c7402824000000c7402c21000000c7403022000000c740340100"
    "0000c7403802000000c7403c08000000c38b4c240883f91073628b54240c803d19ff8b0000751931c0807c0230007508"
    "4083f81c72f3eb088d4101a219ff8b000fb60519ff8b0085c0740f4839c1750431c9eb0685c9750289c183f902731d89"
    "c8c1e00605d840690050526bc11905483f690050e848d0b5ff83c40c31c0c38b450c3b0504798900a304798900741483"
    "f803740583f804750a6a01e8d08cb5ff83c404e93395b7ffc705d844690001000000c705f044690001000000e92f0bba"
    "ffffffffff0000000050460000ffffffff786900000c7b0000e4570000ffffffff2823000094110000bc340000ffffff"
    "ffffffffffffffffffffffffffffffffff00100020004000800001000220001000400080000109080a02060405016690"
    "5bf88b0076f88b0091f88b00aaf88b004b45524e454c33322e646c6c0057494e4d4d2e646c6c002e5c444159544f4e41"
    "2e494e4900536c6565700074696d65426567696e506572696f640057726974655072697661746550726f66696c655374"
    "72696e67410057726974655072697661746550726f66696c6553747275637441004765745072697661746550726f6669"
    "6c65537472696e6741004765745072697661746550726f66696c6553747275637441004765745072697661746550726f"
    "66696c65496e744100526574726f6465636b00506164006e74646c6c2e646c6c0077696e655f6765745f76657273696f"
    "6e0078696e707574315f332e646c6c0078696e707574315f342e646c6c0078696e707574395f315f302e646c6c005849"
    "6e707574476574537461746500"
)
LABELS_SW = {"KFN": 0x8bf000, "PROF": 0x8bf01d, "P_WSTR": 0x8bf040, "P_WBIN": 0x8bf063, "P_RSTR": 0x8bf08d, "P_RBIN": 0x8bf0b5, "INIT": 0x8bf0df, "DUE": 0x8bf11c, "PACE": 0x8bf133, "P_DRAW": 0x8bf1d6, "P_WAIT": 0x8bf1f6, "P_RESYNC": 0x8bf22c, "P_OUT": 0x8bf26c, "PADMODE": 0x8bf279, "NOJOY": 0x8bf2ee, "DIG1": 0x8bf2fd, "DIG2": 0x8bf315, "DIG3": 0x8bf32d, "JOYREAD": 0x8bf345, "J_XOK": 0x8bf3a0, "J_WINMM": 0x8bf466, "J_OK": 0x8bf51d, "J_FAIL": 0x8bf52b, "XLOAD": 0x8bf535, "JCLAMP": 0x8bf57b, "JAX": 0x8bf586, "PAD": 0x8bf598, "KSEL": 0x8bf67b, "PADDEF": 0x8bf69a, "JOYEV": 0x8bf701, "SEQSAVE": 0x8bf76f, "DEFS": 0x8bf798, "XPOV": 0x8bf7b1, "XBTN": 0x8bf7f1, "POVTAB": 0x8bf805, "PNAMES": 0x8bf810, "s_kernel32": 0x8bf820, "s_winmm": 0x8bf82d, "s_ini": 0x8bf837, "n_sleep": 0x8bf845, "n_tbp": 0x8bf84b, "n_wpps": 0x8bf85b, "n_wpst": 0x8bf876, "n_gpps": 0x8bf891, "n_gpst": 0x8bf8aa, "n_gppi": 0x8bf8c3, "s_retro": 0x8bf8d9, "s_padkey": 0x8bf8e3, "s_ntdll": 0x8bf8e7, "n_wgv": 0x8bf8f1, "s_xi13": 0x8bf902, "s_xi14": 0x8bf910, "s_xi910": 0x8bf91e, "n_xgs": 0x8bf92e}

def patches_d3d(L):
    t = lambda va: va - 0x400c00       # .text: VA 0x401000 at file offset 0x400
    d = lambda va: va - (0x4b4000 - 0xb2c00)
    return {
        "nocd":      [(t(0x43ae30), "558bec81ec50", "b801000000c3")],                     # mov eax,1 / ret
        "profile":   [(t(0x418cc1), "558bec81ec", jmp(0x418cc1, L["P_WSTR"])),
                      (t(0x418da4), "558bec81ec", jmp(0x418da4, L["P_WBIN"])),
                      (t(0x418e80), "558bec81ec", jmp(0x418e80, L["P_RSTR"])),
                      (t(0x418f57), "558bec81ec", jmp(0x418f57, L["P_RBIN"]))],
        "cdnotify":  [(t(0x4254a0), "ff0508f14b00", "909090909090"),
                      (t(0x4258c7), "ff0508f14b00", "909090909090")],
        "cdplay":    [(t(0x425b95), "0f8524000000", "90e924000000")],                     # jmp 0x425bbf
        "pace":      [(t(0x448cb4), "8b45fc2b0588e35000", jmp(0x448cb4, L["PACE"]) + b"\x90" * 4)],
        "pad":       [(t(0x45f1fc), "837df0000f8ca0000000", jmp(0x45f1fc, L["PAD"]) + b"\x90" * 5)],
        "paddef":    [(d(0x4d5a74), "34124400", struct.pack("<I", L["PADDEF"]))],
        "defaults":  [(t(0x40d502), "c705e8ce890003000000", "c705e8ce89000b000000"),
                      (t(0x40d5ca), "e8f1550400", call(0x40d5ca, L["DEFS"]))],
        "nojoy":     [(t(0x45ebf9), "e8ec000000", call(0x45ebf9, L["NOJOY"]))],          # joystick enumeration only in pad mode
        "digital":   [(t(0x4232d4), "0f8404000000", jmp(0x4232d4, L["DIG1"]) + b"\x90"), # analogue options only in pad mode
                      (t(0x4232e5), "0f8404000000", jmp(0x4232e5, L["DIG2"]) + b"\x90"),
                      (t(0x4667af), "0f8414000000", jmp(0x4667af, L["DIG3"]) + b"\x90")],
        "autook":    [(t(0x449e87), "b801000000", jmp(0x449e87, L["AUTOOK"]))],
        "ddguid":    [(t(0x469689), "b810f24b0083c02c50", jmp(0x469689, L["DDGUID"]) + b"\x90" * 4)],
        "noconfirm": [(t(0x40cd35), "0f8534000000", "90e934000000")],                     # jmp 0x40cd6f
        "gassel":    [(t(0x441af7), "8b45f88b4d088901", jmp(0x441af7, L["KSEL"]) + b"\x90" * 3)],  # keyboard gas = select, brake = cancel too
        "joyev":     [(t(0x4218ce), "558bec83ec", jmp(0x4218ce, L["JOYEV"]))],
        "seqsave":   [(t(0x45a8af), "8b450ca384668600", jmp(0x45a8af, L["SEQSAVE"]) + b"\x90" * 3)],
        "fogoff":    [(t(0x40d680), "c745e401000000", "c745e400000000")],
        "heapzero":  [(t(0x444785), "506a008b45f850", "506a088b45f850")],                 # HeapAlloc(HEAP_ZERO_MEMORY)
        "coop":      [(t(0x45edc2), "6a09", "6a0a")],                                     # joystick: background, non-exclusive
        "joyread":   [(t(0x45f1b5), "8b45f8508b", jmp(0x45f1b5, L["JOYREAD"]))],          # winmm instead of Poll/GetDeviceState
        "noacq":     [(t(0x45ec3f), "8b45ec508b45ec8b00ff501c", "90" * 12)],              # no Acquire at enumeration
        "noff":      [(t(0x45ec76), "0f8435000000", "90e935000000"),                      # enumeration: never the FF set-up
                      (t(0x441c93), "0f840e000000", "90e90e000000"),                      # no SendForceFeedbackCommand(STOPALL)
                      (t(0x441cf7), "0f847b000000", "90e97b000000"),                      # no effect stop pass
                      (t(0x43cb0d), "0f8407000000", "90e907000000")],                     # "is FF device" -> 0
    }

def patches_sw(L):
    t = lambda va: va - 0x400c00       # .text: VA 0x401000 at file offset 0x400
    d = lambda va: va - (0x4b2000 - 0xb0200)
    return {
        "nocd":      [(t(0x416530), "558bec81ec50", "b801000000c3")],
        "profile":   [(t(0x4272b1), "558bec81ec", jmp(0x4272b1, L["P_WSTR"])),
                      (t(0x427394), "558bec81ec", jmp(0x427394, L["P_WBIN"])),
                      (t(0x427470), "558bec81ec", jmp(0x427470, L["P_RSTR"])),
                      (t(0x427547), "558bec81ec", jmp(0x427547, L["P_RBIN"]))],
        "cdnotify":  [(t(0x42bf32), "ff05c0cc4c00", "909090909090"),
                      (t(0x42c35c), "ff05c0cc4c00", "909090909090")],
        "cdplay":    [(t(0x42c62b), "0f8524000000", "90e924000000")],                     # jmp 0x42c655
        "pace":      [(t(0x4622b4), "8b45fc2b0540235100", jmp(0x4622b4, L["PACE"]) + b"\x90" * 4)],
        "pad":       [(t(0x43dd46), "837df0000f8ca0000000", jmp(0x43dd46, L["PAD"]) + b"\x90" * 5)],
        "paddef":    [(d(0x4c6cc4), "34c34100", struct.pack("<I", L["PADDEF"]))],
        "defaults":  [(t(0x418986), "c705c846690003000000", "c705c84669000b000000"),
                      (t(0x418a4e), "e88d780400", call(0x418a4e, L["DEFS"]))],
        "nojoy":     [(t(0x43d619), "e80a020000", call(0x43d619, L["NOJOY"]))],
        "digital":   [(t(0x402c31), "0f8404000000", jmp(0x402c31, L["DIG1"]) + b"\x90"),
                      (t(0x402c42), "0f8404000000", jmp(0x402c42, L["DIG2"]) + b"\x90"),
                      (t(0x4313ff), "0f8414000000", jmp(0x4313ff, L["DIG3"]) + b"\x90")],
        "noconfirm": [(t(0x44f8b5), "0f8534000000", "90e934000000")],                     # jmp 0x44f8ef
        "gassel":    [(t(0x41cbf7), "8b45f88b4d088901", jmp(0x41cbf7, L["KSEL"]) + b"\x90" * 3)],
        "joyev":     [(t(0x401308), "558bec83ec", jmp(0x401308, L["JOYEV"]))],
        "seqsave":   [(t(0x438cc3), "8b450ca304798900", jmp(0x438cc3, L["SEQSAVE"]) + b"\x90" * 3)],
        "mode16":    [(t(0x418ca2), "c705f85f890002000000", "c705f85f890003000000")],
        "coop":      [(t(0x43d900), "6a09", "6a0a")],
        "joyread":   [(t(0x43dcff), "8b45f8508b", jmp(0x43dcff, L["JOYREAD"]))],          # (no Acquire at enumeration here)
        "noff":      [(t(0x43d68a), "0f8437000000", "90e937000000"),
                      (t(0x41cd93), "0f840e000000", "90e90e000000"),
                      (t(0x415d7d), "0f8407000000", "90e907000000")],
    }

#            original size, new section RVA, cave, labels, patches
TARGETS = {1096704: ("Direct3D", 0x4c1000, lambda: CAVE_D3D, lambda: LABELS_D3D, patches_d3d),
           1081856: ("software", 0x4bf000, lambda: CAVE_SW, lambda: LABELS_SW, patches_sw)}
SEC_HDR = 0x268                        # free room after the 6 section headers in both exes

def patch(data, path="exe"):
    """Returns `data` (either exe, original) with every patch applied; exits (nothing written) on unexpected bytes."""
    data = bytearray(data)
    for size, (name, sec_va, cave, labels, patches) in TARGETS.items():
        cave = cave(); raw = (len(cave) + 0x1ff) & ~0x1ff
        if len(data) in (size, size + raw): break
    else:
        sys.exit(f"{path}: {len(data)} bytes, not one of the two Daytona USA Deluxe exes (or patched by another version); nothing written")
    print(f"  {path}: the {name} exe")
    hdr = struct.pack("<8sIIII12xI", b".ddx", 0x1000, sec_va, raw, size, 0xe0000020)   # rwx code, raw at the old end
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    if len(data) == size:                                        # untouched exe: add the section
        if data[SEC_HDR:SEC_HDR + 40] != bytes(40) or struct.unpack_from("<H", data, pe + 6)[0] != 6 \
           or struct.unpack_from("<I", data, pe + 0x50)[0] != sec_va:
            sys.exit(f"{path}: not the expected header; nothing written")
        data[SEC_HDR:SEC_HDR + 40] = hdr
        struct.pack_into("<H", data, pe + 6, 7)
        struct.pack_into("<I", data, pe + 0x50, sec_va + 0x1000)
        data += cave + bytes(raw - len(cave))
        print("  section: added")
    elif bytes(data[SEC_HDR:SEC_HDR + 40]) == hdr:
        if bytes(data[size:size + len(cave)]) != cave:
            sys.exit(f"{path}: .ddx holds other code (an older patch_exe.py?); start from the original exe")
        print("  section: already applied")
    else:
        sys.exit(f"{path}: unexpected section header; nothing written")
    for pname, edits in patches(labels()).items():
        state = set()
        for off, old, new in edits:
            old = bytes.fromhex(old) if isinstance(old, str) else old
            new = bytes.fromhex(new) if isinstance(new, str) else new
            assert len(old) == len(new), pname
            cur = bytes(data[off:off + len(old)])
            state.add("new" if cur == new else "old" if cur == old else "bad")
        if state == {"new"}: print(f"  {pname}: already applied"); continue
        if state != {"old"}: sys.exit(f"{path}: {pname}: unexpected bytes, not this exe? nothing written")
        for off, old, new in edits:
            new = bytes.fromhex(new) if isinstance(new, str) else new
            data[off:off + len(new)] = new
        print(f"  {pname}: applied")
    return bytes(data)

def main(path):
    open(path, "wb").write(patch(open(path, "rb").read(), path))


if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
