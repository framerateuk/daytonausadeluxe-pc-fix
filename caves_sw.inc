# Daytona USA Deluxe, software exe (the disc's "DAYTONA USA Deluxe.exe", 11 Sep 1997, ver.1.08E, shipped as
# "DAYTONA USA Deluxe SW.exe"): addresses for caves.s (the same functions as the D3D exe, found by code match)
.set BASE,        0x8bf000      # the added section .ddx (RVA 0x4bf000)
.set IMP_GMH,     0x89c588      # GetModuleHandleA
.set IMP_GPA,     0x89c5c8      # GetProcAddress
.set IMP_TGT,     0x89c7dc      # timeGetTime
.set IMP_JOYPOS,  0x89c7e0      # joyGetPosEx
.set IMP_LLA,     0x89c5b0      # LoadLibraryA
.set G_DEVS,      0x896024      # the 16 DirectInput joystick devices
.set IMP_SEND,    0x89c770      # SendMessageA (unused here)
.set G_PLAST,     0x512340      # frame pacer 0x46229f: time of the last decision
.set G_PRESET,    0x512374      # pacer reset flag (set by the reset 0x4621b0)
.set G_PDRAW,     0x512378      # draw this turn
.set G_PTICK,     0x51237c      # logic tick this turn
.set G_PSTATS,    0x462741      # pacer: the 1-second statistics, then return
.set G_POLLOK,    0x43dd50      # joystick poll 0x43dcb0: state read, go on
.set G_POLLFAIL,  0x43ddf0      # joystick poll: next device
.set G_MAPPER,    0x41c7b1      # joystick state -> player record
.set G_LAYOUTS,   0x6940d8      # pad layouts (DAYTONA_PROTECTED_OBJECT 0x693e80 + 0x258)
.set G_RECORDS,   0x693f48      # joystick input records (0x693e80 + 0xc8)
.set G_ANALOG1,   0x6944d8      # player 1 Analog Steering Control (0x693e80 + 0x658)
.set G_ANALOG2,   0x6944f0      # player 2
.set G_DEFSRET,   0x4602e0      # the call DEFS replaces
.set G_SEQ,       0x897904      # current sequence
.set G_SEQRET,    0x438ccb      # sequence change 0x438c90: after the store
.set G_SAVEALL,   0x418460      # load (0) / save (1) every setting and record
.set V_INIT,   BASE + 0xf00
# run-time pad switch
.set G_ENUMJOY,   0x43d828
.set G_D1T,       0x402c3b
.set G_D1N,       0x402c37
.set G_D2T,       0x402c4c
.set G_D2N,       0x402c48
.set G_D3T,       0x431419
.set G_D3N,       0x431405
# keyboard select / cancel
.set G_KSELRET,   0x41cbff      # keyboard mapper 0x441a97 (SW 0x41cb97): after the mask store
