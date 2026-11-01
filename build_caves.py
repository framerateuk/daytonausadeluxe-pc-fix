#!/usr/bin/env python3
"""Assemble caves.s (Daytona USA Deluxe's code caves) for both exes and print the labels; compare with patch_exe.py.

    python3 build_caves.py           print, and compare with patch_exe.py
    python3 build_caves.py --write   also rewrite CAVE and LABELS in patch_exe.py

Needs clang (any build that targets i686: Apple's does). Only needed to change a cave: assemble.sh uses
the bytes already in patch_exe.py. caves.s is assembled twice, after caves_d3d.inc (the Direct3D exe, section
.ddx at 0x8c1000) and after caves_sw.inc (the software exe, .ddx at 0x8bf000): CAVE_D3D / LABELS_D3D and
CAVE_SW / LABELS_SW in patch_exe.py.
"""
import os, re, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "caves.s")
ROOM = 0xf00                           # code up to the variables at BASE + 0xf00
TARGETS = {"D3D": "caves_d3d.inc", "SW": "caves_sw.inc"}


def elf_text(obj):
    """(.text bytes, {label: offset}, [offsets of R_386_32 relocations against .text])"""
    d = open(obj, "rb").read()
    shoff, = struct.unpack_from("<I", d, 0x20)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 0x2e)
    secs = [struct.unpack_from("<IIIIIIIIII", d, shoff + i * shentsize) for i in range(shnum)]
    names = secs[shstrndx]
    nm = lambda off: d[names[4] + off:d.index(b"\0", names[4] + off)].decode()
    by = {nm(s[0]): (i, s) for i, s in enumerate(secs)}
    ti, ts = by[".text"]
    text = bytearray(d[ts[4]:ts[4] + ts[5]])
    _, sym = by[".symtab"]
    strtab = secs[sym[6]]
    syms = []
    for k in range(sym[5] // 16):
        st_name, st_value, st_size, st_info, st_other, st_shndx = struct.unpack_from("<IIIBBH", d, sym[4] + 16 * k)
        name = d[strtab[4] + st_name:d.index(b"\0", strtab[4] + st_name)].decode()
        syms.append((name, st_value, st_shndx))
    labels = {n: v for n, v, sh in syms if sh == ti and n and not n.startswith(".")}
    rels = []
    if ".rel.text" in by:
        _, rs = by[".rel.text"]
        for k in range(rs[5] // 8):
            off, info = struct.unpack_from("<II", d, rs[4] + 8 * k)
            typ, si = info & 0xFF, info >> 8
            name, value, shndx = syms[si]
            if typ != 1 or shndx != ti:
                sys.exit(f"unexpected relocation type {typ} against {name!r} at .text+{off:#x}")
            rels.append(off)
            struct.pack_into("<I", text, off, struct.unpack_from("<I", text, off)[0] + value)
    return text, labels, rels


def assemble(inc):
    incsrc = open(os.path.join(HERE, inc)).read()
    base = int(re.search(r"^\.set BASE,\s*(0x[0-9a-f]+)", incsrc, re.M).group(1), 16)
    with tempfile.TemporaryDirectory() as t:
        src, obj = os.path.join(t, "caves.s"), os.path.join(t, "caves.o")
        open(src, "w").write(incsrc + "\n" + open(SRC).read())
        subprocess.run(["clang", "-target", "i686-pc-linux-gnu", "-c", "-x", "assembler", src, "-o", obj], check=True)
        text, labels, rels = elf_text(obj)
    for off in rels:                      # PUSHADDR label: add the section's address
        struct.pack_into("<I", text, off, struct.unpack_from("<I", text, off)[0] + base)
    if len(text) > ROOM:
        sys.exit(f"caves: {len(text)} bytes, room for {ROOM}")
    return base, bytes(text), {k: base + v for k, v in labels.items() if k != "A"}


def main():
    pe = os.path.join(HERE, "patch_exe.py")
    src = open(pe).read()
    allsame = True
    for tgt, inc in TARGETS.items():
        base, code, labels = assemble(inc)
        print(f"{tgt}: caves at {base:#x}: {len(code)} bytes")
        for k, v in sorted(labels.items(), key=lambda kv: kv[1]):
            print(f"   {v:#x} {k}")
        m = re.search(r'^CAVE_%s = bytes\.fromhex\(\n((?:    "[0-9a-f]*"\n)+)\)' % tgt, src, re.M)
        cur = bytes.fromhex("".join(re.findall(r'"([0-9a-f]*)"', m.group(1)))) if m else None
        lt = re.search(r"^LABELS_%s = \{.*?\}\n" % tgt, src, re.M | re.S)
        want = "LABELS_%s = {%s}\n" % (tgt, ", ".join(f'"{k}": {v:#x}' for k, v in sorted(labels.items(), key=lambda kv: kv[1])))
        same = cur == code and lt is not None and lt.group(0) == want
        print(f"patch_exe.py {tgt}", "matches" if same else "DIFFERS")
        if "--write" in sys.argv and not same:
            if not (m and lt):
                sys.exit(f"patch_exe.py has no CAVE_{tgt} / LABELS_{tgt} block to rewrite")
            h = code.hex()
            new = f"CAVE_{tgt} = bytes.fromhex(\n" + "".join(f'    "{h[i:i + 96]}"\n' for i in range(0, len(h), 96)) + ")"
            src = src[:m.start()] + new + src[m.end():]
            lt = re.search(r"^LABELS_%s = \{.*?\}\n" % tgt, src, re.M | re.S)
            src = src[:lt.start()] + want + src[lt.end():]
            open(pe, "w").write(src)
            print(f"patch_exe.py {tgt} written")
            same = True
        allsame &= same
    return 0 if allsame else 1


if __name__ == "__main__":
    sys.exit(main())
