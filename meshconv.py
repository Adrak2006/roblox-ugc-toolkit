#!/usr/bin/env python3
"""Roblox .mesh (v1 - v7) -> .obj + .mtl.  Uso: meshconv.py in.mesh out.obj [textura.png]"""
import sys, re, struct, pathlib

def load(path):
    raw = pathlib.Path(path).read_bytes()
    nl = raw.index(b"\n"); ver = raw[8:nl].decode().strip(); body = raw[nl+1:]
    major = int(float(ver))

    if major == 1:                                        # ASCII
        lines = body.split(b"\n"); nf = int(lines[0])
        n = [float(x) for x in re.findall(rb"-?\d+\.?\d*(?:[eE]-?\d+)?", lines[1])]
        sc = 0.5 if ver.startswith("1.00") else 1.0
        V  = [tuple(v*sc for v in n[i*9:i*9+3]) for i in range(nf*3)]
        UV = [(n[i*9+6], n[i*9+7])              for i in range(nf*3)]
        return ver, V, UV, [(i*3,i*3+1,i*3+2) for i in range(nf)]

    if major == 7:                                        # COREMESH + Draco
        import DracoPy
        assert body[:8] == b"COREMESH"
        dlen, = struct.unpack_from("<I", body, 16)
        m = DracoPy.decode(body[20:20+dlen])
        return ver, list(map(tuple, m.points)), list(map(tuple, m.tex_coord)), list(map(tuple, m.faces))

    if major in (2, 3):
        hsz, vsz, fsz = struct.unpack_from("<HBB", body, 0); o = 4
        nlod = 0
        if major == 3:
            _lsz, nlod = struct.unpack_from("<HH", body, o); o += 4
        nv, nf = struct.unpack_from("<II", body, o); o = hsz
        nbones = 0
    else:                                                 # 4.xx / 5.xx / 6.xx
        hsz, _lodtype, nv, nf, nlod, nbones = struct.unpack_from("<HHIIHH", body, 0)
        vsz, fsz, o = 40, 12, hsz

    V = [struct.unpack_from("<3f", body, o + i*vsz)      for i in range(nv)]
    UV = [struct.unpack_from("<2f", body, o + i*vsz + 24) for i in range(nv)]
    o += nv*vsz
    if nbones: o += nv*8                                  # envelopes de skinning
    F = [struct.unpack_from("<3I", body, o + i*fsz) for i in range(nf)]
    o += nf*fsz
    if nlod > 1:                                          # quedarse solo con el LOD0
        lods = struct.unpack_from(f"<{nlod}I", body, o)
        F = F[lods[0]:lods[1]]
    return ver, V, UV, F

def write_obj(out, V, UV, F, tex=None):
    out = pathlib.Path(out); mtl = out.with_suffix(".mtl")
    with open(out, "w") as f:
        if tex: f.write(f"mtllib {mtl.name}\n")
        f.write(f"o {out.stem}\n")
        for v in V:  f.write("v %.6f %.6f %.6f\n" % tuple(v))
        for t in UV: f.write("vt %.6f %.6f\n" % (t[0], 1.0 - t[1]))
        if tex: f.write("usemtl material0\n")
        for a,b,c in F: f.write(f"f {a+1}/{a+1} {b+1}/{b+1} {c+1}/{c+1}\n")
    if tex:
        mtl.write_text(f"newmtl material0\nKa 1 1 1\nKd 1 1 1\nd 1\nillum 2\n"
                       f"map_Kd {tex}\nmap_d {tex}\n")

if __name__ == "__main__":
    ver, V, UV, F = load(sys.argv[1])
    write_obj(sys.argv[2], V, UV, F, sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"  v{ver}: {len(V)} verts / {len(F)} tris -> {sys.argv[2]}")
