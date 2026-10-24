#!/usr/bin/env python3
"""Convierte una malla Roblox v7.00 (COREMESH + Draco) a .obj"""
import sys, struct, pathlib, DracoPy

def chunks(body):
    assert body[:8] == b"COREMESH", "no es COREMESH"
    n, total, first_len = struct.unpack_from("<III", body, 8)
    o, out = 20, []
    out.append(("DRACO", body[o:o+first_len])); o += first_len
    while o + 4 <= len(body):                       # chunks restantes: id4 + payload
        cid = body[o:o+4]; o += 4
        out.append((cid.decode('latin1'), body[o:]))
        break
    return out

def convert(path, out_obj, out_mtl=None, tex=None):
    raw = pathlib.Path(path).read_bytes()
    nl = raw.index(b"\n"); ver = raw[8:nl].decode().strip(); body = raw[nl+1:]
    print(f"  version {ver}")
    ck = dict((k, v) for k, v in chunks(body))
    m = DracoPy.decode(ck["DRACO"])
    V, F = m.points, m.faces
    UV = getattr(m, "tex_coord", None)
    N  = getattr(m, "normals", None)
    print(f"  {len(V)} vertices / {len(F)} triangulos / uv={'si' if UV is not None and len(UV) else 'no'} "
          f"normales={'si' if N is not None and len(N) else 'no'}")
    with open(out_obj, "w") as f:
        if out_mtl: f.write(f"mtllib {out_mtl}\n")
        f.write(f"o {pathlib.Path(path).stem}\n")
        for v in V: f.write("v %.6f %.6f %.6f\n" % tuple(v))
        has_uv = UV is not None and len(UV) == len(V)
        has_n  = N  is not None and len(N)  == len(V)
        if has_uv:
            for t in UV: f.write("vt %.6f %.6f\n" % (t[0], t[1]))
        if has_n:
            for n in N: f.write("vn %.6f %.6f %.6f\n" % tuple(n))
        if out_mtl: f.write("usemtl material0\n")
        for tri in F:
            f.write("f " + " ".join(
                f"{i+1}" + (f"/{i+1}" if has_uv else ("/" if has_n else "")) +
                (f"/{i+1}" if has_n else "") for i in tri) + "\n")
    if out_mtl and tex:
        pathlib.Path(out_obj).with_suffix(".mtl").write_text(
            f"newmtl material0\nKa 1 1 1\nKd 1 1 1\nd 1\nillum 2\nmap_Kd {tex}\nmap_d {tex}\n")
    return len(V), len(F)

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2],
            out_mtl=pathlib.Path(sys.argv[2]).with_suffix(".mtl").name,
            tex=sys.argv[3] if len(sys.argv) > 3 else None)
