#!/usr/bin/env python3
"""Build a ready-to-run Daytona USA Deluxe folder for modern PCs from your own CD (and Sega's Direct3D patch).

Usage:
  python3 build.py DISC.cue|DISC.ccd [--d3d-patch ddx_d3d.exe] --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip
                   [--out DIR] [--windows]

  DISC          your Daytona USA Deluxe CD (Sega PC, 1997; the European / US English disc, "ver.1.08E") as
                .cue + .bin or .ccd + .img, with its audio tracks
  --d3d-patch   Sega's official "Daytona USA Deluxe - Direct 3D Patch" (ddx_d3d.exe, ver.1.20E, 640,932 bytes);
                without it you get the disc's software-rendered exe only
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm release zip (or folder)
  --out         where to create DaytonaUSADeluxe/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc and the patch.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, patch_exe

EXE = "DAYTONA USA Deluxe.exe"
DISC_EXE_MD5 = "c1e334a15d9472219441ed5f2bb89fb1"       # GAME\DAYTONA USA Deluxe.exe, 11 Sep 1997, ver.1.08E (software)
PATCH_MD5 = "f4a3cc1397792307e18b5aec7b74d2ef"          # ddx_d3d.exe, the WinZip self-extractor
D3D_EXE_MD5 = "61a168d474f6bab8fdeffc3a1058082e"        # its game\DAYTONA USA Deluxe.exe, 23 Dec 1997, ver.1.20E
D3D_PATCHED_MD5 = "3eca7f03cf1582ceb478737a4d47860f"
SW_PATCHED_MD5 = "346d2811c7f9a2db4f9926d9ab1e5163"
STEP = 1764                                              # 40 ms at 44.1 kHz
TRACKS = 23                                              # audio tracks 2-24


def md5(data): return hashlib.md5(data).hexdigest()


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def last_granule(path):                   # total samples of a single-stream Ogg Vorbis file
    d = open(path, "rb").read(); i = d.rfind(b"OggS")
    return struct.unpack_from("<q", d, i + 6)[0] if i >= 0 else -1


def rip(tracks, music):
    """Each track from its INDEX 01 to the next track's start, minus up to 2 s of digital silence at the end, then
    padded with silence to 1764 * k + 1 samples: exactly k * 40 ms. The game plays a track as "from the position of
    track N to the position of track N+1", positions it asked for in MSF (1/75 s frames); ogg-winmm keeps its track
    starts in whole milliseconds and rounds both ways down, so unless every start is a multiple of 40 ms (3 frames,
    the only exact ms <-> frame steps) a play starts with the last milliseconds of the previous song. The extra
    sample keeps the truncation of k * 0.04 s from falling to 40k - 1 ms."""
    enc = encoder(); os.makedirs(music, exist_ok=True); zero = bytes(2352); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)
            tail = 0
            while tail < 150 and data[len(data) - (tail + 1) * 2352:len(data) - tail * 2352] == zero: tail += 1
            if tail: data = data[:len(data) - tail * 2352]
            samples = len(data) // 4
            target = ((samples - 1 + STEP - 1) // STEP) * STEP + 1 if samples > 1 else 1
            data += bytes(4 * (target - samples))
            wav = os.path.join(tmp, f"track{t.n:02d}.wav"); ogg = os.path.join(music, f"Track{t.n:02d}.ogg")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, ogg), check=True); os.remove(wav)
            if last_granule(ogg) != target: sys.exit(f"Track{t.n:02d}: the encoder changed its length; try oggenc")
            print(f"  Music/Track{t.n:02d}.ogg  {(target - 1) // STEP * 40 / 1000:6.2f} s"); n += 1
    if n != TRACKS: sys.exit(f"expected {TRACKS} audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f: f.write(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--d3d-patch")
    ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    entries = {p.upper(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk(joliet=True)}
    key = ("GAME/" + EXE).upper()
    if key not in entries: sys.exit(f"no GAME\\{EXE} on this CD: it isn't the Daytona USA Deluxe PC disc")
    disc_exe = dt.read_file(*entries[key][2:])
    if md5(disc_exe) != DISC_EXE_MD5:
        sys.exit(f"this CD's {EXE} is not the ver.1.08E exe the kit was made for (MD5 {md5(disc_exe)}); "
                 "other versions aren't supported")

    patch = None
    if a.d3d_patch:
        raw = open(a.d3d_patch, "rb").read()
        if md5(raw) != PATCH_MD5:
            sys.exit(f"{a.d3d_patch} is not Sega's ddx_d3d.exe ver.1.20E (MD5 {md5(raw)})")
        z = zipfile.ZipFile(a.d3d_patch)               # a WinZip self-extractor: a plain zip after the stub
        patch = {i.filename.replace("\\", "/"): z.read(i) for i in z.infolist() if not i.is_dir()}
        if md5(patch["game/" + EXE]) != D3D_EXE_MD5: sys.exit("unexpected exe in the Direct3D patch")

    pkg = os.path.join(os.path.abspath(a.out), "DaytonaUSADeluxe"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    # What the retail installer's full install put in C:\SEGA\DAYTONA USA Deluxe: the disc's GAME\ (with Resource\)
    # and the English help; everything is opened by bare name from the working directory once the CD check is gone
    print("1/5 game files from the CD" + (" and the Direct3D patch" if patch else ""))
    for k, (p, is_dir, l, s) in entries.items():
        if is_dir or not k.startswith("GAME/"): continue
        rel = p.split("/", 1)[1]
        if rel == EXE: continue
        if patch and rel.lower() in ("resource.dll", "dpctrl.dll"): continue      # the patch's supersets replace them
        dt.copy_file(l, s, os.path.join(game, *rel.split("/")))
    for name in ("DAYTONA USA Deluxe.hlp", "DAYTONA USA Deluxe.cnt"):            # F1 help (English)
        dt.copy_file(*entries[("DOC/ENGLISH/" + name).upper()][2:], os.path.join(game, name))
    write(os.path.join(game, "_spare", "DAYTONA USA Deluxe_disc.exe"), disc_exe)
    if patch:
        write(os.path.join(game, "RESOURCE.DLL"), patch["game/RESOURCE.DLL"])
        write(os.path.join(game, "DPCTRL.dll"), patch["game/DPCTRL.dll"])
        for name, b in patch.items():                                            # the time-of-day course pictures
            if name.lower().startswith("game/resource/640x480x16/mode/"):
                write(os.path.join(game, "Resource", "640X480X16", "MODE", name.rsplit("/", 1)[1]), b)
        write(os.path.join(game, "DDX_FAQ.TXT"), patch["ddx_faq.txt"])
        write(os.path.join(game, "_spare", "DAYTONA USA Deluxe_d3d.exe"), patch["game/" + EXE])

    print("2/5 exe patches")
    sw = patch_exe.patch(disc_exe, "DAYTONA USA Deluxe SW.exe")
    if md5(sw) != SW_PATCHED_MD5: sys.exit("patching gave an unexpected software exe")
    write(os.path.join(game, "DAYTONA USA Deluxe SW.exe"), sw)
    if patch:
        d3d = patch_exe.patch(patch["game/" + EXE], EXE)
        if md5(d3d) != D3D_PATCHED_MD5: sys.exit("patching gave an unexpected Direct3D exe")
        write(os.path.join(game, EXE), d3d)

    print("3/5 soundtrack (each track padded to whole 40 ms)")
    rip(tracks, os.path.join(game, "Music"))

    print("4/5 wrappers and settings")
    write(os.path.join(game, "ddraw.dll"), take(a.dgvoodoo, "MS/x86/DDraw.dll"))
    write(os.path.join(game, "D3DImm.dll"), take(a.dgvoodoo, "MS/x86/D3DImm.dll"))
    write(os.path.join(game, "winmm.dll"), take(a.ogg_winmm, "winmm.dll"))
    for name in ("dgVoodooD3D.conf", "dgVoodooSW.conf", "winmm.ini"):
        shutil.copyfile(os.path.join(HERE, "config", name), os.path.join(game, name))
    # dgVoodoo reads dgVoodoo.conf; on the Deck the launch script copies the one for the exe being started over it
    shutil.copyfile(os.path.join(HERE, "config", "dgVoodooD3D.conf" if patch else "dgVoodooSW.conf"),
                    os.path.join(game, "dgVoodoo.conf"))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "daytonadx_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "daytonadx_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
