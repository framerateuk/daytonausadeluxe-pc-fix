# Daytona USA Deluxe, Direct3D exe (the patch's "DAYTONA USA Deluxe.exe", 23 Dec 1997, ver.1.20E): addresses for caves.s
.set D3D, 1
.set BASE,        0x8c1000      # the added section .ddx (RVA 0x4c1000)
.set IMP_GMH,     0x89f5f8      # GetModuleHandleA
.set IMP_GPA,     0x89f628      # GetProcAddress
.set IMP_TGT,     0x89f7f4      # timeGetTime
.set IMP_JOYPOS,  0x89f810      # joyGetPosEx
.set IMP_LLA,     0x89f604      # LoadLibraryA
.set G_DEVS,      0x864c24      # the 16 DirectInput joystick devices
.set IMP_SEND,    0x89f780      # SendMessageA
.set G_PLAST,     0x50e388      # frame pacer: time of the last decision
.set G_PRESET,    0x50e3bc      # pacer reset flag (set by the reset 0x448bb0)
.set G_PDRAW,     0x50e3c0      # draw this turn (event 0xe)
.set G_PTICK,     0x50e3c4      # logic tick this turn (events 0x10-0x12, 0x19)
.set G_PSTATS,    0x449141      # pacer: the 1-second statistics, then return
.set G_POLLOK,    0x45f206      # joystick poll 0x45f166: state read, go on
.set G_POLLFAIL,  0x45f2a6      # joystick poll: next device
.set G_MAPPER,    0x4416b1      # joystick state -> player record (record, state, layout)
.set G_LAYOUTS,   0x89c8f8      # pad layouts, 0x40 per player (DAYTONA_PROTECTED_OBJECT 0x89c6a0 + 0x258)
.set G_RECORDS,   0x89c768      # joystick input records, 0x19 per player (0x89c6a0 + 0xc8)
.set G_ANALOG1,   0x89ccf8      # player 1 Analog Steering Control (0x89c6a0 + 0x658)
.set G_ANALOG2,   0x89cd10      # player 2
.set G_DEFSRET,   0x452bc0      # the call DEFS replaces (records defaults)
.set G_SEQ,       0x866684      # current sequence
.set G_SEQRET,    0x45a8b7      # sequence change 0x45a87c: after the store
.set G_SAVEALL,   0x40cfd0      # load (0) / save (1) every setting and record
.set G_DLGOK,     0x449d6a      # "Direct3D" driver dialog: OK handler
.set G_DLGINITRET,0x449e91      # its WM_INITDIALOG: epilogue
.set G_DDPRIMARY, 0x4bf238      # chosen driver is the primary one
.set G_DDGUID,    0x4bf23c      # chosen driver's GUID
.set G_DDCREATE,  0x469692      # call 0x45764e (DirectDrawCreate of the chosen driver)
.set V_INIT,   BASE + 0xf00     # variables past the raw data (zero at load)
# run-time pad switch
.set G_ENUMJOY,   0x45ecea
.set G_D1T,       0x4232de
.set G_D1N,       0x4232da
.set G_D2T,       0x4232ef
.set G_D2N,       0x4232eb
.set G_D3T,       0x4667c9
.set G_D3N,       0x4667b5
# keyboard select / cancel
.set G_KSELRET,   0x441aff      # keyboard mapper 0x441a97 (SW 0x41cb97): after the mask store
