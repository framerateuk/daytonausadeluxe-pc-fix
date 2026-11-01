# Daytona USA Deluxe: the code caves for both exes, the source of CAVE_D3D / CAVE_SW in patch_exe.py
# (docs/TECHNICAL.md).
#
#   python3 build_caves.py           assemble with clang (i686 ELF) after
#   python3 build_caves.py --write   caves_d3d.inc and after caves_sw.inc, print
#                                                                       the labels, compare with / rewrite patch_exe.py
#
# Everything lives in a section patch_exe.py adds to each exe (".ddx", the 7th section header in the free
# header space at 0x268): VA 0x8c1000 in the Direct3D exe, 0x8bf000 in the software exe (right after .reloc),
# raw data appended at the old end of the file, read/write/execute. The variables sit at BASE + 0xf00, past
# the raw data, so they are zero at load. Targets in the original exe are written "A + (G_x - BASE)" so clang
# resolves them as plain rel32 (no relocation); PUSHADDR label and [label + reg] leave R_386_32 relocations
# that build_caves.py adds BASE to. Addresses quoted in the comments below are the Direct3D exe's; both
# exes' are in the .inc files.

.intel_syntax noprefix

.macro PUSHADDR lab               # push imm32 of a label (clang's intel mode makes "push offset" 16-bit)
    .byte 0x68
    .long \lab
.endm

# Per-exe addresses (G_*, IMP_*, BASE, V_*) come from caves_d3d.inc or caves_sw.inc, which build_caves.py puts
# in front of this file; D3D is defined only for the Direct3D exe (AUTOOK and DDGUID exist only there).

                                # V_INIT (per exe: BASE + 0xf00): pacer INIT done
.set V_SLEEP,  V_INIT + 0x04    # Sleep (0 = not available)
.set V_T0,     V_INIT + 0x08    # pacer: time of tick 0 (ms)
.set V_K,      V_INIT + 0x0c    # pacer: ticks run since V_T0
.set V_R,      V_INIT + 0x10    # pacer: ticks per second the schedule was made for
.set V_SKIP,   V_INIT + 0x14    # pacer: drawings skipped in a row
.set V_ZOK,    V_INIT + 0x18    # byte: the Z axis (triggers) has been seen resting in the middle
.set V_ACT,    V_INIT + 0x19    # byte: DirectInput device that is player 1, + 1 (0 = none yet; JOYEV)
.set V_XTRY,   V_INIT + 0x1a    # byte: XInput looked up (JOYREAD)
.set V_XOK,    V_INIT + 0x1b    # byte: XInputGetState has answered once (no winmm from then on)
.set V_PADINIT,V_INIT + 0x1c    # byte: PADMODE decided
.set V_PADON,  V_INIT + 0x1d    # byte: 1 = the game reads the pad (Windows), 0 = keys only (Wine)
.set V_XGS,    V_INIT + 0x30    # XInputGetState (0 = none)
.set V_PROF,   V_INIT + 0x20    # 4 dwords: WritePrivateProfileStringA, WritePrivateProfileStructA,
                                #           GetPrivateProfileStringA, GetPrivateProfileStructA (0 = not looked up)

.text
A:

# KFN(name), stdcall: GetProcAddress(GetModuleHandleA("KERNEL32.dll"), name) or 0
KFN:
    PUSHADDR s_kernel32
    call dword ptr [IMP_GMH]
    test eax, eax
    jz 1f
    push dword ptr [esp+4]
    push eax
    call dword ptr [IMP_GPA]
1:  ret 4

# PROF: eax = the profile function V_PROF[ecx] (looked up once; ecx = 0..3), 0 if missing; ZF set if 0
PROF:
    mov eax, dword ptr [V_PROF + ecx*4]
    test eax, eax
    jnz 1f
    push ecx
    push dword ptr [PNAMES + ecx*4]
    call KFN
    pop ecx
    mov dword ptr [V_PROF + ecx*4], eax
    test eax, eax
1:  ret

# The four registry helpers (cdecl; they wrote HKCU\Software\SEGA\DAYTONA USA Deluxe\Profile\<section>) now
# use .\DAYTONA.INI, [section] key=value. The last argument (the registry base key) is not needed.
# After pushing k dwords the caller's argument n sits at [esp + 4*n + 4*k].

# 0x418cc1 WriteString(section, key, string, base) -> 1 written, 0 not
P_WSTR:
    xor ecx, ecx
    call PROF
    jz 1f
    PUSHADDR s_ini
    push dword ptr [esp+16]     # string
    push dword ptr [esp+16]     # key
    push dword ptr [esp+16]     # section
    call eax                    # WritePrivateProfileStringA
1:  neg eax
    sbb eax, eax
    neg eax
    ret

# 0x418da4 WriteBinary(section, key, data, size, base) -> 1 written, 0 not
P_WBIN:
    mov ecx, 1
    call PROF
    jz 1f
    PUSHADDR s_ini
    push dword ptr [esp+20]     # size
    push dword ptr [esp+20]     # data
    push dword ptr [esp+20]     # key
    push dword ptr [esp+20]     # section
    call eax                    # WritePrivateProfileStructA
1:  neg eax
    sbb eax, eax
    neg eax
    ret

# 0x418e80 ReadString(section, key, default, buffer, size, base) -> characters copied (default if missing)
P_RSTR:
    mov ecx, 2
    call PROF
    jz 1f
    PUSHADDR s_ini
    push dword ptr [esp+24]     # size
    push dword ptr [esp+24]     # buffer
    push dword ptr [esp+24]     # default
    push dword ptr [esp+24]     # key
    push dword ptr [esp+24]     # section
    call eax                    # GetPrivateProfileStringA
1:  ret

# 0x418f57 ReadBinary(section, key, buffer, size, base) -> 1 read (exactly size bytes, checksum right), 0 not
P_RBIN:
    mov ecx, 3
    call PROF
    jz 1f
    PUSHADDR s_ini
    push dword ptr [esp+20]     # size
    push dword ptr [esp+20]     # buffer
    push dword ptr [esp+20]     # key
    push dword ptr [esp+20]     # section
    call eax                    # GetPrivateProfileStructA
1:  neg eax
    sbb eax, eax
    neg eax
    ret

# INIT (first PACE call): Sleep from KERNEL32, timeBeginPeriod(1) from WINMM (Sleep(1) and timeGetTime 1 ms
# precise on Windows; Wine is already). The exe imports neither.
INIT:
    mov dword ptr [V_INIT], 1
    PUSHADDR n_sleep
    call KFN
    mov dword ptr [V_SLEEP], eax
    PUSHADDR s_winmm
    call dword ptr [IMP_GMH]
    test eax, eax
    jz 1f
    PUSHADDR n_tbp
    push eax
    call dword ptr [IMP_GPA]
    test eax, eax
    jz 1f
    push 1
    call eax
1:  ret

# DUE: eax = due time of tick V_K + 1 = V_T0 + (V_K + 1) * 1000 / ecx (ecx = ticks per second, kept)
DUE:
    mov eax, dword ptr [V_K]
    inc eax
    imul eax, eax, 1000
    xor edx, edx
    div ecx
    add eax, dword ptr [V_T0]
    ret

# PACE (0x448cb4, inside the frame pacer 0x448c9f(ticks per second); [ebp+8] = 60 or 30, [ebp-4] = now from
# timeGetTime): a fixed schedule, tick k due at T0 + k * 1000 / R ms, instead of "a whole period since the
# last decision" (whole milliseconds: 34 ms = 29.4 Hz for a 30 Hz race, 17 ms = 58.8 Hz for 60 Hz menus),
# and a sleep instead of the spin until the next tick. Late by a period or more: the tick runs without a
# drawing (at most 3 in a row); late by 125 ms or more (a stall, a loading): the schedule restarts.
# Sets 0x50e3c0 (draw) / 0x50e3c4 (logic tick) and goes on to the original 1-second statistics (0x449141).
PACE:
    cmp dword ptr [V_INIT], 0
    jne 1f
    call INIT
1:  mov ecx, dword ptr [ebp+8]
    test ecx, ecx
    jnz 2f
    mov ecx, 60
2:  cmp dword ptr [G_PRESET], 0     # reset by 0x448bb0 (start, sequence change, reactivation)
    jne P_RESYNC
    cmp ecx, dword ptr [V_R]
    jne P_RESYNC
    call DUE
    mov edx, dword ptr [ebp-4]
    sub edx, eax                    # now - due
    js P_WAIT
    cmp edx, 125
    jge P_RESYNC
    inc dword ptr [V_K]             # the tick runs
    mov eax, ecx
    imul eax, eax, 60               # every minute of ticks: T0 on by 60000 ms (no overflow in DUE)
    cmp dword ptr [V_K], eax
    jb 3f
    sub dword ptr [V_K], eax
    add dword ptr [V_T0], 60000
3:  call DUE                        # the next tick's due time
    mov edx, dword ptr [ebp-4]
    sub edx, eax
    js P_DRAW                       # on time: draw
    cmp dword ptr [V_SKIP], 3
    jae P_DRAW
    inc dword ptr [V_SKIP]          # a period behind: tick without drawing
    mov dword ptr [G_PDRAW], 0
    mov dword ptr [G_PTICK], 1
    jmp P_OUT
P_DRAW:
    mov dword ptr [V_SKIP], 0
    mov dword ptr [G_PDRAW], 1
    mov dword ptr [G_PTICK], 1
    jmp P_OUT
P_WAIT:
    mov dword ptr [G_PDRAW], 0
    mov dword ptr [G_PTICK], 0
    neg edx                         # ms until the tick
    cmp edx, 3
    jb P_OUT                        # the last 2 ms are polled
    sub edx, 2
    cmp edx, 20
    jbe 4f
    mov edx, 20
4:  mov eax, dword ptr [V_SLEEP]
    test eax, eax
    jz P_OUT
    push edx
    call eax                        # Sleep
    jmp P_OUT
P_RESYNC:
    mov dword ptr [V_R], ecx
    mov eax, dword ptr [ebp-4]
    mov dword ptr [V_T0], eax
    mov dword ptr [V_K], 0
    mov dword ptr [V_SKIP], 0
    mov dword ptr [G_PRESET], 0
    mov dword ptr [G_PDRAW], 1
    mov dword ptr [G_PTICK], 1
P_OUT:
    mov eax, dword ptr [ebp-4]
    mov dword ptr [G_PLAST], eax
    jmp A + (G_PSTATS - BASE)

# PADMODE: eax = 1 if the game reads the pad, 0 if not (decided once, at the first call: the joystick set-up at
# start). .\DAYTONA.INI [Retrodeck] Pad=1 / Pad=0 decides if present; otherwise off under Wine (ntdll exports
# wine_get_version: Proton / the Steam Deck, where Wine's reads of the pad fail at random moments in this game's
# process, docs/TECHNICAL.md; the pad then reaches the game as keys through Steam Input) and on under Windows.
PADMODE:
    movzx eax, byte ptr [V_PADON]
    cmp byte ptr [V_PADINIT], 0
    jne 9f
    mov byte ptr [V_PADINIT], 1
    PUSHADDR n_gppi
    call KFN
    test eax, eax
    jz 2f
    PUSHADDR s_ini
    push -1
    PUSHADDR s_padkey
    PUSHADDR s_retro
    call eax                        # GetPrivateProfileIntA("Retrodeck", "Pad", -1, ".\DAYTONA.INI")
    cmp eax, -1
    je 2f
    test eax, eax
    setnz al
    movzx eax, al
    jmp 8f
2:  PUSHADDR s_ntdll
    call dword ptr [IMP_GMH]
    test eax, eax
    jz 3f
    PUSHADDR n_wgv
    push eax
    call dword ptr [IMP_GPA]
    test eax, eax
    jz 3f
    xor eax, eax                    # Wine: no pad
    jmp 8f
3:  mov eax, 1                      # Windows: pad
8:  mov byte ptr [V_PADON], al
9:  ret

# NOJOY (replaces the call of the joystick enumeration 0x45ecea at 0x45ebf9, cdecl, 5 arguments already pushed):
# pad mode on -> the original enumeration (tail jump), off -> nothing, so no DirectInput joystick device exists
# and Wine starts no reader for one.
NOJOY:
    call PADMODE
    test eax, eax
    jz 1f
    jmp A + (G_ENUMJOY - BASE)
1:  ret

# DIG1 / DIG2 / DIG3 (in place of the je after "cmp dword ptr [eax], 0" at 0x4232d4, 0x4232e5 (race set-up 0x4232b0:
# Analog Steering, Analog Gas/Brake) and 0x4667af (steering curve choice 0x466792)): pad mode off -> always the
# digital branch (the keys, the Saturn pad's steering curve 0x4e5cb8), on -> the player's option as before.
# Every branch target reloads eax.
DIG1:
    jz A + (G_D1T - BASE)
    call PADMODE
    test eax, eax
    jz A + (G_D1T - BASE)
    jmp A + (G_D1N - BASE)
DIG2:
    jz A + (G_D2T - BASE)
    call PADMODE
    test eax, eax
    jz A + (G_D2T - BASE)
    jmp A + (G_D2N - BASE)
DIG3:
    jz A + (G_D3T - BASE)
    call PADMODE
    test eax, eax
    jz A + (G_D3T - BASE)
    jmp A + (G_D3N - BASE)

# JOYREAD (replaces, at 0x45f1b5, the per-device Poll + GetDeviceState + Acquire-on-failure of the joystick
# poll 0x45f166; [ebp-4] = device index, [ebp-0xc] = its DIJOYSTATE buffer, [ebp-0x10] = result): pad mode off
# -> unplugged. On: fills the DIJOYSTATE from XInputGetState(0) (xinput1_3 / 1_4 / 9_1_0), else - only if
# XInput is missing or has never answered - from winmm joyGetPosEx(0); then on to PAD as before. Only device 0.
# XInput -> the DInput view Proton gives the same pad: lX / lY = left stick (Y down-positive), lZ = (LT - RT) / 2
# (left trigger high, right low, 0 at rest), lRx / lRy = right stick, lRz and sliders 0, POV 0 from the D-pad,
# rgbButtons 0-9 = A B X Y LB RB Back Start L3 R3. Axes -127..127 (the range the game set, 0x45ef37).
JOYREAD:
    mov dword ptr [ebp-0x10], -1
    cmp dword ptr [ebp-4], 0
    jne A + (G_POLLFAIL - BASE)
    call PADMODE
    test eax, eax
    jz A + (G_POLLFAIL - BASE)
    push esi
    push edi
    sub esp, 0x34
    cmp byte ptr [V_XTRY], 0
    jne 1f
    call XLOAD
1:  mov eax, dword ptr [V_XGS]
    test eax, eax
    jz J_WINMM                      # no XInput at all: winmm
    mov ecx, esp
    push ecx
    push 0
    call eax                        # XInputGetState(0, &state)
    test eax, eax
    jz J_XOK
    cmp byte ptr [V_XOK], 0
    jne J_FAIL                      # XInput worked before: the pad is gone, never winmm
    jmp J_WINMM
J_XOK:
    mov byte ptr [V_XOK], 1
    mov edi, dword ptr [ebp-0xc]
    movsx eax, word ptr [esp+8]     # sThumbLX
    sar eax, 8
    call JCLAMP
    mov dword ptr [edi], eax
    movsx eax, word ptr [esp+0xa]   # sThumbLY (up-positive) -> lY down-positive
    sar eax, 8
    neg eax
    call JCLAMP
    mov dword ptr [edi+4], eax
    movzx eax, byte ptr [esp+6]     # bLeftTrigger
    movzx ecx, byte ptr [esp+7]     # bRightTrigger
    sub eax, ecx
    sar eax, 1
    call JCLAMP
    mov dword ptr [edi+8], eax      # lZ
    movsx eax, word ptr [esp+0xc]   # sThumbRX
    sar eax, 8
    call JCLAMP
    mov dword ptr [edi+0xc], eax    # lRx
    movsx eax, word ptr [esp+0xe]   # sThumbRY
    sar eax, 8
    neg eax
    call JCLAMP
    mov dword ptr [edi+0x10], eax   # lRy
    xor eax, eax
    mov dword ptr [edi+0x14], eax   # lRz
    mov dword ptr [edi+0x18], eax   # sliders
    mov dword ptr [edi+0x1c], eax
    movzx eax, word ptr [esp+4]     # wButtons: D-pad bits 1 up, 2 down, 4 left, 8 right
    and eax, 0xf
    mov eax, dword ptr [XPOV + eax*4]
    mov dword ptr [edi+0x20], eax
    mov dword ptr [edi+0x24], -1
    mov dword ptr [edi+0x28], -1
    mov dword ptr [edi+0x2c], -1
    push edi
    add edi, 0x30
    xor eax, eax
    mov ecx, 8
    rep stosd                       # rgbButtons 0-31 released
    pop edi
    movzx edx, word ptr [esp+4]
    xor ecx, ecx
2:  movzx eax, word ptr [XBTN + ecx*2]
    test edx, eax
    jz 3f
    mov byte ptr [edi+0x30+ecx], 0x80
3:  inc ecx
    cmp ecx, 10
    jb 2b
    jmp J_OK
J_WINMM:
    mov dword ptr [esp], 0x34       # JOYINFOEX.dwSize
    mov dword ptr [esp+4], 0xff     # JOY_RETURNALL
    push esp
    push 0
    call dword ptr [IMP_JOYPOS]     # joyGetPosEx(0, &ji)
    test eax, eax
    jnz J_FAIL
    mov edi, dword ptr [ebp-0xc]
    mov eax, dword ptr [esp+0x08]   # X
    call JAX
    mov dword ptr [edi], eax
    mov eax, dword ptr [esp+0x0c]   # Y
    call JAX
    mov dword ptr [edi+4], eax
    mov eax, dword ptr [esp+0x10]   # Z
    call JAX
    mov dword ptr [edi+8], eax
    mov eax, dword ptr [esp+0x18]   # U
    call JAX
    mov dword ptr [edi+0xc], eax
    mov eax, dword ptr [esp+0x1c]   # V
    call JAX
    mov dword ptr [edi+0x10], eax
    mov eax, dword ptr [esp+0x14]   # R
    call JAX
    mov dword ptr [edi+0x14], eax
    mov dword ptr [edi+0x18], 0
    mov dword ptr [edi+0x1c], 0
    movzx eax, word ptr [esp+0x28]  # dwPOV
    cmp eax, 0xffff
    jne 4f
    or eax, -1
4:  mov dword ptr [edi+0x20], eax
    mov dword ptr [edi+0x24], -1
    mov dword ptr [edi+0x28], -1
    mov dword ptr [edi+0x2c], -1
    mov edx, dword ptr [esp+0x20]   # dwButtons
    xor ecx, ecx
5:  xor eax, eax
    shr edx, 1
    jnc 6f
    mov al, 0x80
6:  mov byte ptr [edi+0x30+ecx], al
    inc ecx
    cmp ecx, 32
    jb 5b
J_OK:
    mov dword ptr [ebp-0x10], 0
    add esp, 0x34
    pop edi
    pop esi
    jmp PAD
J_FAIL:
    add esp, 0x34
    pop edi
    pop esi
    jmp A + (G_POLLFAIL - BASE)

# XLOAD (first JOYREAD): V_XGS = XInputGetState from xinput1_3.dll, else xinput1_4.dll, else xinput9_1_0.dll
XLOAD:
    mov byte ptr [V_XTRY], 1
    PUSHADDR s_xi13
    call dword ptr [IMP_LLA]
    test eax, eax
    jnz 1f
    PUSHADDR s_xi14
    call dword ptr [IMP_LLA]
    test eax, eax
    jnz 1f
    PUSHADDR s_xi910
    call dword ptr [IMP_LLA]
    test eax, eax
    jz 9f
1:  PUSHADDR n_xgs
    push eax
    call dword ptr [IMP_GPA]
    mov dword ptr [V_XGS], eax
9:  ret

# JCLAMP: eax -> at least -127 (signed 8-bit stick values give -128..127)
JCLAMP:
    cmp eax, -127
    jge 1f
    mov eax, -127
1:  ret

# JAX: eax = winmm axis 0..65535 -> -127..127
JAX:
    and eax, 0xffff
    imul eax, eax, 255
    shr eax, 16
    sub eax, 127
    ret

# PAD (0x45f1fc, the per-frame DirectInput joystick poll 0x45f166, right after GetDeviceState; [ebp-0x10] =
# its result, [ebp-0xc] = the DIJOYSTATE, axes -127..127): changes the state before the game's mapping
# (0x4416b1) and its "anything pressed" test see it:
#   buttons 29 / 30 / 31 (rgbButtons[28..30], free on any pad) = A or right trigger / B or left trigger /
#   LB or RB (the triggers share Z: right pulls it low, left high; counted only after Z has been seen in the
#   middle, so a throttle resting at one end does nothing); a 6 % dead zone on X, the rest scaled to full
#   lock; the D-pad (POV hat, ignored by the game) pushes X / Y to their ends in 8 directions.
PAD:
    cmp dword ptr [ebp-0x10], 0
    jl A + (G_POLLFAIL - BASE)
    push ebx
    mov ecx, dword ptr [ebp-0xc]
    mov eax, dword ptr [ecx+8]      # Z
    cmp eax, -0x20
    jl 1f
    cmp eax, 0x20
    jg 1f
    mov byte ptr [V_ZOK], 1
1:  mov bl, byte ptr [ecx+0x30]     # A
    cmp byte ptr [V_ZOK], 0
    je 2f
    cmp eax, -0x30
    jg 2f
    mov bl, 0x80                    # right trigger past 38 %
2:  mov byte ptr [ecx+0x30+28], bl
    mov bl, byte ptr [ecx+0x31]     # B
    cmp byte ptr [V_ZOK], 0
    je 3f
    cmp eax, 0x30
    jl 3f
    mov bl, 0x80                    # left trigger past 38 %
3:  mov byte ptr [ecx+0x30+29], bl
    mov bl, byte ptr [ecx+0x34]     # LB
    or bl, byte ptr [ecx+0x35]      # RB
    mov byte ptr [ecx+0x30+30], bl
    mov eax, dword ptr [ecx]        # X: dead zone 8 of 127
    mov ebx, eax
    sar ebx, 31
    xor eax, ebx
    sub eax, ebx
    sub eax, 8
    jg 4f
    xor eax, eax
    jmp 5f
4:  imul eax, eax, 127
    push ecx
    mov ecx, 119
    xor edx, edx
    div ecx
    pop ecx
    cmp eax, 127
    jbe 5f
    mov eax, 127
5:  xor eax, ebx
    sub eax, ebx
    mov dword ptr [ecx], eax
    mov eax, dword ptr [ecx+0x20]   # POV 0: centred = low word 0xffff, else hundredths of a degree
    cmp ax, 0xffff
    je 9f
    movzx eax, ax
    cmp eax, 36000
    jae 9f
    add eax, 2250
    push ecx
    mov ecx, 4500
    xor edx, edx
    div ecx
    pop ecx
    movzx eax, byte ptr [POVTAB + eax]
    test al, 1
    jz 6f
    mov dword ptr [ecx+4], -127     # up
6:  test al, 2
    jz 7f
    mov dword ptr [ecx+4], 127      # down
7:  test al, 4
    jz 8f
    mov dword ptr [ecx], -127       # left
8:  test al, 8
    jz 9f
    mov dword ptr [ecx], 127        # right
9:  pop ebx
    jmp A + (G_POLLOK - BASE)

# KSEL (0x441af7, the keyboard mapper 0x441a97 storing the 16-slot mask it built from the key states; from the
# per-tick 0x421981, players 1 and 2): the Gas slot (bit 0) also sets Select (bit 13, 0x2000), so the gas key
# (X; the Deck's A and right trigger through Steam Input) selects in the menus as Enter does;
# and the Brake slot (bit 1) also sets Cancel (bit 14, 0x4000), so the brake key (Z; the Deck's X and left
# trigger) goes back as Esc does. In a race the race handlers test Cancel only in the pause screen,
# where it resumes the race (Arcade 0x41771c -> 0x417846, Time Attack 0x403a2d, 2P 0x43bd4a).
# In a race Select is read only by the pause menu (0x4176ba: Select or Start on a new press picks the item);
# the race handler itself tests Start (pause) and View Change only (0x41767e), and new presses are counted per
# slot (0x441bae), so a held gas pedal never repeats a selection.
KSEL:
    mov eax, dword ptr [ebp-8]
    test al, 1
    jz 1f
    or eax, 0x2000                  # Gas -> also Select
1:  test al, 2
    jz 2f
    or eax, 0x4000                  # Brake -> also Cancel
2:  mov ecx, dword ptr [ebp+8]
    mov dword ptr [ecx], eax
    jmp A + (G_KSELRET - BASE)

# PADDEF (table 0x4d5a48 entry 11, the default layout for a joystick whose name is none of the 11 the game
# knows; cdecl, arg = the 16 slots): codes 1-32 = button n, 0x21 + 2 * axis = axis low, + 1 = axis high
# (axes X Y Z Rx Ry Rz). The game's own default had gears on stick up / down, view on X and no Start.
PADDEF:
    push edi
    mov edi, dword ptr [esp+8]
    xor eax, eax
    mov ecx, 16
    rep stosd
    pop edi
    mov eax, dword ptr [esp+4]
    mov dword ptr [eax], 29         # Gas: A or right trigger (PAD)
    mov dword ptr [eax+4], 30       # Brake: B or left trigger (PAD)
    mov dword ptr [eax+8], 4        # Shift Up: Y
    mov dword ptr [eax+12], 3       # Shift Down: X
    mov dword ptr [eax+0x20], 31    # View Change: LB or RB (PAD)
    mov dword ptr [eax+0x24], 0x23  # Up: stick / D-pad up
    mov dword ptr [eax+0x28], 0x24  # Down
    mov dword ptr [eax+0x2c], 0x21  # Left
    mov dword ptr [eax+0x30], 0x22  # Right
    mov dword ptr [eax+0x34], 1     # Select: A
    mov dword ptr [eax+0x38], 2     # Cancel: B
    mov dword ptr [eax+0x3c], 8     # Start: Menu
    ret

.ifdef D3D
# AUTOOK (0x449e87, end of WM_INITDIALOG of the "Direct3D" driver dialog 0x8a that 0x44a135 opened at every
# start; [ebp-4] = its list box, filled by DirectDrawEnumerateA, [ebp+8] -> the dialog handle): select the
# first driver with DDCAPS_3D (item data + 0; else the first) and run the dialog's OK handler 0x449d6a
# (the item copied to 0x4bf230, EndDialog), so the dialog never needs a mouse click.
AUTOOK:
    push esi
    push edi
    mov esi, dword ptr [ebp-4]
    push 0
    push 0
    push 0x18b                      # LB_GETCOUNT
    push esi
    call dword ptr [IMP_SEND]
    test eax, eax
    jle 9f
    mov edi, eax
    push ebx
    xor ebx, ebx
1:  push 0
    push ebx
    push 0x199                      # LB_GETITEMDATA
    push esi
    call dword ptr [IMP_SEND]
    cmp eax, -1
    je 2f
    cmp dword ptr [eax], 0          # DDCAPS_3D
    jne 3f
2:  inc ebx
    cmp ebx, edi
    jb 1b
    xor ebx, ebx
3:  push 0
    push ebx
    push 0x186                      # LB_SETCURSEL
    push esi
    call dword ptr [IMP_SEND]
    push dword ptr [ebp+8]
    call A + (G_DLGOK - BASE)
    add esp, 4
    pop ebx
9:  pop edi
    pop esi
    mov eax, 1
    jmp A + (G_DLGINITRET - BASE)

# DDGUID (0x469689, the DirectDrawCreate of the chosen driver, 0x45764e(&guid, ...)): NULL (the active
# display driver) when the chosen item is the primary driver, whose GUID the game stored as all zeros
DDGUID:
    cmp dword ptr [G_DDPRIMARY], 0
    je 1f
    push 0
    jmp A + (G_DDCREATE - BASE)
1:  push G_DDGUID
    jmp A + (G_DDCREATE - BASE)

.endif

# JOYEV (replaces 0x4218ce, the handler of event 0x12 "joystick n has input", cdecl (event, device, DIJOYSTATE)):
# the original mapped DirectInput device n to player n (n < 2: layout 0x89c6a0 + 0x258 + n*0x40, record
# 0x89c6a0 + 0xc8 + n*0x19, mapper 0x4416b1). The menus take input from any player (0x421d52 posts event 0x13
# for all 8), but the race only from player 1 (0x421a25 posts record 0; 0x41763a ignores other players), so a
# pad that DirectInput does not list first worked in the menus and was dead in the race (seen on the Steam Deck,
# 18 Oct 2026: menus fine, no gas, steering, view or pause in the race). Now the first device whose real
# buttons (rgbButtons 0-27) are pressed becomes player 1 for the session and device 0 takes its place.
JOYEV:
    mov ecx, dword ptr [esp+8]      # device index (0x45f166 loop)
    cmp ecx, 16
    jae 9f
    mov edx, dword ptr [esp+12]     # its DIJOYSTATE
    cmp byte ptr [V_ACT], 0
    jne 2f
    xor eax, eax
1:  cmp byte ptr [edx+0x30+eax], 0
    jne 3f
    inc eax
    cmp eax, 28
    jb 1b
    jmp 2f
3:  lea eax, [ecx+1]
    mov byte ptr [V_ACT], al        # active device + 1
2:  movzx eax, byte ptr [V_ACT]
    test eax, eax
    jz 4f
    dec eax
    cmp ecx, eax
    jne 5f
    xor ecx, ecx                    # the active device -> player 1
    jmp 4f
5:  test ecx, ecx
    jnz 4f
    mov ecx, eax                    # device 0 -> the active device's old place
4:  cmp ecx, 2
    jae 9f
    mov eax, ecx
    shl eax, 6
    add eax, G_LAYOUTS               # layout of player ecx
    push eax
    push edx
    imul eax, ecx, 0x19
    add eax, G_RECORDS               # input record of player ecx
    push eax
    call A + (G_MAPPER - BASE)
    add esp, 12
9:  xor eax, eax
    ret

# SEQSAVE (0x45a8af, the sequence change 0x45a87c: [G_SEQ] = new sequence): on entering the title (3) or the
# mode select (4) from another sequence, save everything as the exit does (0x40cfd0(1): records, options,
# layouts -> DAYTONA.INI), so quitting through Steam (which ends the process without WM_CLOSE) loses nothing.
# Settings are loaded (0x422ace) before the sequence handler that leads here is installed.
SEQSAVE:
    mov eax, dword ptr [ebp+0xc]
    cmp eax, dword ptr [G_SEQ]
    mov dword ptr [G_SEQ], eax
    je 1f
    cmp eax, 3
    je 2f
    cmp eax, 4
    jne 1f
2:  push 1
    call A + (G_SAVEALL - BASE)
    add esp, 4
1:  jmp A + (G_SEQRET - BASE)

# DEFS (end of 0x40d4fc, the defaults used when the saved DAYTONA_PROTECTED_OBJECT is missing): "Analog Steering
# Control" on for both players (used only in pad mode, see DIG1-3), then the original call
DEFS:
    mov dword ptr [G_ANALOG1], 1
    mov dword ptr [G_ANALOG2], 1
    jmp A + (G_DEFSRET - BASE)

XPOV:   .long -1, 0, 18000, -1, 27000, 31500, 22500, -1, 9000, 4500, 13500, -1, -1, -1, -1, -1
XBTN:   .short 0x1000, 0x2000, 0x4000, 0x8000, 0x0100, 0x0200, 0x0020, 0x0010, 0x0040, 0x0080  # A B X Y LB RB Back Start L3 R3
POVTAB: .byte 1, 9, 8, 10, 2, 6, 4, 5, 1    # octant N NE E SE S SW W NW N -> 1 up, 2 down, 4 left, 8 right
.p2align 2
PNAMES: .long n_wpps, n_wpst, n_gpps, n_gpst
s_kernel32: .asciz "KERNEL32.dll"
s_winmm:    .asciz "WINMM.dll"
s_ini:      .asciz ".\\DAYTONA.INI"
n_sleep:    .asciz "Sleep"
n_tbp:      .asciz "timeBeginPeriod"
n_wpps:     .asciz "WritePrivateProfileStringA"
n_wpst:     .asciz "WritePrivateProfileStructA"
n_gpps:     .asciz "GetPrivateProfileStringA"
n_gpst:     .asciz "GetPrivateProfileStructA"
n_gppi:     .asciz "GetPrivateProfileIntA"
s_retro:    .asciz "Retrodeck"
s_padkey:   .asciz "Pad"
s_ntdll:    .asciz "ntdll.dll"
n_wgv:      .asciz "wine_get_version"
s_xi13:     .asciz "xinput1_3.dll"
s_xi14:     .asciz "xinput1_4.dll"
s_xi910:    .asciz "xinput9_1_0.dll"
n_xgs:      .asciz "XInputGetState"
