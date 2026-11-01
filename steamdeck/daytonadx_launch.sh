#!/bin/bash
# Daytona USA Deluxe (Sega PC, 1997) Steam Deck / Proton launch wrapper, for both exes in game/:
#   "DAYTONA USA Deluxe.exe"     Sega's official Direct3D patch (ver.1.20E): hardware 3D, no bonnet view
#   "DAYTONA USA Deluxe SW.exe"  the disc's original software renderer (ver.1.08E): all four views
#
# One Steam shortcut per exe, both with these Launch Options:
#   /home/deck/Games/DaytonaUSADeluxe/daytonadx_launch.sh %command%
# Shortcut target: "/home/deck/Games/DaytonaUSADeluxe/game/DAYTONA USA Deluxe.exe" (or ... SW.exe),
#   Start In: /home/deck/Games/DaytonaUSADeluxe/game/
#
# Both exes are patched (patch_exe.py): no CD check, settings and records in game/DAYTONA.INI instead of the
# registry, CD music that keeps looping under ogg-winmm, a fixed 30 / 60 Hz frame schedule without a busy wait,
# no "Direct3D" driver dialog and no "Exit game ?" dialog. Under Wine the game reads the keyboard only (Wine's
# reads of the pad stall in this game, docs/TECHNICAL.md); a Steam Input layout turns the Deck's pad into keys.
#
# Every launch sets DLL overrides so Wine loads the wrappers sitting beside the exe:
#   winmm.dll    ogg-winmm: CD audio from Music/TrackNN.ogg
#   ddraw.dll    dgVoodoo2 2.79.3: DirectDraw  } -> D3D11 -> DXVK; the game's 640x480 Direct3D picture rendered
#   d3dimm.dll   dgVoodoo2 2.79.3: Direct3D    }    at the screen's height (dgVoodoo.conf [DirectX] Resolution)
# dgVoodoo reads game/dgVoodoo.conf; this script copies game/dgVoodooD3D.conf or game/dgVoodooSW.conf (software
# exe: 640x480 16-bit DirectDraw, no forced resolution) over it before each start.
#
# RENDERER (set before the script path in Launch Options, default dgvoodoo):
#   dgvoodoo  ddraw + d3dimm from dgVoodoo2
#   wined3d   plain Wine ddraw / d3d (640x480, no upscaling)
#   Example:  RENDERER=wined3d /home/deck/Games/DaytonaUSADeluxe/daytonadx_launch.sh %command%

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/launch.log"
# A file RENDERER beside this script holding e.g. wined3d wins over the default (switch it from Desktop Mode).
[ -z "${RENDERER:-}" ] && [ -s "$HERE/RENDERER" ] && RENDERER="$(tr -d ' \n' < "$HERE/RENDERER")"
RENDERER="${RENDERER:-dgvoodoo}"
log() { echo "[$(date '+%H:%M:%S')] $*" >>"$LOG"; }
: >"$LOG"
log "args: $*"
log "RENDERER=$RENDERER  STEAM_COMPAT_DATA_PATH=${STEAM_COMPAT_DATA_PATH:-unset}"

# Proton appends its own overrides after ours.
OVR="winmm=n,b"
case "$RENDERER" in
  dgvoodoo) OVR="$OVR;ddraw=n,b;d3dimm=n,b" ;;
  wined3d)  OVR="$OVR;ddraw=b;d3dimm=b" ;;
  *)        log "unknown RENDERER '$RENDERER', using dgvoodoo"; OVR="$OVR;ddraw=n,b;d3dimm=n,b" ;;
esac
export WINEDLLOVERRIDES="${OVR}${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
log "WINEDLLOVERRIDES=$WINEDLLOVERRIDES"

# Debugging: if a file named PROTON_LOG exists beside this script, Proton writes
# steam-<appid>.log here (crash addresses, exceptions). Create / delete it from Desktop Mode; no launch-option edit.
if [ -e "$HERE/PROTON_LOG" ]; then
  export PROTON_LOG=1 PROTON_LOG_DIR="$HERE"
  log "PROTON_LOG on -> $HERE/steam-*.log"
  # Extra Wine debug channels for that log: a file WINEDEBUG beside this script holding e.g. +ddraw
  if [ -s "$HERE/WINEDEBUG" ]; then
    export WINEDEBUG="+timestamp,+tid,+seh,+loaddll,$(tr -d ' \n' < "$HERE/WINEDEBUG")"
    log "WINEDEBUG=$WINEDEBUG"
  fi
fi

# Frame rate / GPU load overlay (DXVK, on top of dgVoodoo's D3D11): a file DXVK_HUD beside this script
# holding e.g. fps,gpuload. Create / delete it from Desktop Mode.
if [ -s "$HERE/DXVK_HUD" ]; then
  export DXVK_HUD="$(tr -d ' \n' < "$HERE/DXVK_HUD")"
  log "DXVK_HUD=$DXVK_HUD"
fi

# The exe being started decides the dgVoodoo settings.
case "$*" in
  *"Deluxe SW.exe"*) CONF=dgVoodooSW.conf ;;
  *)                 CONF=dgVoodooD3D.conf ;;
esac
if [ -s "$HERE/game/$CONF" ]; then cp -f "$HERE/game/$CONF" "$HERE/game/dgVoodoo.conf" && log "dgVoodoo.conf <- $CONF"
else log "WARNING: game/$CONF missing, dgVoodoo.conf left as it is"; fi

for f in "DAYTONA USA Deluxe SW.exe" ddse.dll DXERROR.dll WINCPUID.DLL \
         Resource/course0.mdl Resource/22_8_mo00.bin \
         winmm.dll winmm.ini ddraw.dll D3DImm.dll dgVoodoo.conf Music/Track02.ogg Music/Track24.ogg; do
  [ -e "$HERE/game/$f" ] || log "WARNING: game/$f missing"
done
[ -e "$HERE/game/DAYTONA USA Deluxe.exe" ] || log "no Direct3D exe (built without --d3d-patch): software exe only"
[ -e "$HERE/game/DAYTONA.INI" ] && log "DAYTONA.INI present (settings, records)" || log "no DAYTONA.INI yet: first run, game defaults"

log "exec: $*"
exec "$@"
