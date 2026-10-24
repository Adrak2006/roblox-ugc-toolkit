#!/usr/bin/env python3
"""Descarga un asset de Roblox (accesorio/modelo) y extrae mallas + texturas.

Uso:  ROBLOSECURITY=<cookie> python3 rbxrip.py <assetId> [outdir]
      (PLACE_ID=<id> opcional, para assets que solo se sirven dentro de un juego)
"""
import os, re, sys, json, struct, pathlib
import requests
import lz4.block

COOKIE = os.environ.get("ROBLOSECURITY", "").strip()
PLACE_ID = os.environ.get("PLACE_ID", "").strip()   # opcional: assets de un juego
S = requests.Session()
S.headers["User-Agent"] = "Roblox/WinInet"
if PLACE_ID:
    S.headers["Roblox-Place-Id"] = PLACE_ID
if COOKIE:
    S.cookies.set(".ROBLOSECURITY", COOKIE, domain=".roblox.com")

def whoami():
    r = S.get("https://users.roblox.com/v1/users/authenticated", timeout=30)
    if r.status_code == 200:
        u = r.json(); print(f"[*] sesion OK: {u['name']} (id {u['id']})"); return True
    print(f"[!] sesion NO valida (HTTP {r.status_code}) -> la cookie esta caducada o mal copiada")
    return False

# ---------------------------------------------------------------- descarga
def fetch_asset(aid):
    r = S.get("https://assetdelivery.roblox.com/v1/asset/", params={"id": aid}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"asset {aid}: HTTP {r.status_code} {r.text[:200]}")
    return r.content

# ------------------------------------------------- parser rbxm (binario/XML)
def rbxm_strings(data: bytes) -> bytes:
    """Devuelve todos los bytes de propiedades (descomprimidos) de un .rbxm."""
    if not data.startswith(b"<roblox!"):
        return data                      # XML plano u otra cosa: se usa tal cual
    out = bytearray()
    pos = 16 + 16                        # firma + (classCount, instCount, reserved)
    while pos + 16 <= len(data):
        name = data[pos:pos+4]
        clen, ulen, _ = struct.unpack_from("<III", data, pos+4)
        pos += 16
        payload = data[pos:pos+(clen if clen else ulen)]
        pos += (clen if clen else ulen)
        if clen:
            try:
                payload = lz4.block.decompress(payload, uncompressed_size=ulen)
            except Exception:
                pass                     # zstd u otro: se ignora ese chunk
        out += payload
        if name == b"END\x00":
            break
    return bytes(out)

REF = re.compile(rb"(?:rbxassetid://|roblox\.com/asset/?\?id=)(\d{5,})", re.I)

def find_refs(data: bytes):
    seen, order = set(), []
    for m in REF.finditer(rbxm_strings(data)):
        i = m.group(1).decode()
        if i not in seen:
            seen.add(i); order.append(i)
    return order

# ----------------------------------------------------- parser .mesh -> .obj
def parse_mesh(b: bytes):
    if not b.startswith(b"version "):
        raise ValueError("no es un .mesh de Roblox")
    nl = b.index(b"\n")
    ver = b[8:nl].decode().strip()
    body = b[nl+1:]
    major = int(float(ver))

    if major == 1:                       # ASCII
        lines = body.split(b"\n")
        nfaces = int(lines[0])
        nums = [float(x) for x in re.findall(rb"-?\d+\.?\d*(?:e-?\d+)?", lines[1])]
        scale = 0.5 if ver.startswith("1.00") else 1.0
        V, UV, F = [], [], []
        for i in range(nfaces * 3):
            o = i * 9
            V.append(tuple(n * scale for n in nums[o:o+3]))
            UV.append((nums[o+6], nums[o+7]))
        F = [(i*3, i*3+1, i*3+2) for i in range(nfaces)]
        return ver, V, UV, F

    o = 0
    if major in (2, 3):
        hsz, vsz, fsz = struct.unpack_from("<HBB", body, o); o += 4
        if major == 3:
            _lodsz, nlod = struct.unpack_from("<HH", body, o); o += 4
        else:
            nlod = 0
        nv, nf = struct.unpack_from("<II", body, o); o += 8
    else:                                # 4, 5, 6, 7...
        hsz, = struct.unpack_from("<H", body, 0)
        _lodtype, nv, nf, nlod, nbones = struct.unpack_from("<HIIHH", body, 2)
        vsz, fsz = 40, 12
        o = hsz
        if nbones:
            pass                         # envelopes se saltan más abajo

    V, UV, F = [], [], []
    for i in range(nv):
        px, py, pz, nx, ny, nz, tu, tv = struct.unpack_from("<8f", body, o + i*vsz)
        V.append((px, py, pz)); UV.append((tu, tv))
    o += nv * vsz
    if major >= 4:
        nbones = struct.unpack_from("<H", body, 8)[0] if hsz >= 16 else 0
        if nbones:
            o += nv * 8                  # 4 bone idx + 4 pesos por vértice
    for i in range(nf):
        a, c, d = struct.unpack_from("<3I", body, o + i*fsz)
        F.append((a, c, d))
    return ver, V, UV, F

def write_obj(path, name, V, UV, F, mtl=None):
    with open(path, "w") as f:
        if mtl: f.write(f"mtllib {mtl}\n")
        f.write(f"o {name}\n")
        for v in V:  f.write("v %.6f %.6f %.6f\n" % v)
        for t in UV: f.write("vt %.6f %.6f\n" % (t[0], 1.0 - t[1]))
        if mtl: f.write("usemtl material0\n")
        for a, b, c in F:
            f.write(f"f {a+1}/{a+1} {b+1}/{b+1} {c+1}/{c+1}\n")

# ----------------------------------------------------------------- main
def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    aid = sys.argv[1]
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    out.mkdir(parents=True, exist_ok=True)

    if not COOKIE:
        sys.exit("[!] falta ROBLOSECURITY")
    if not whoami():
        sys.exit(1)

    root = fetch_asset(aid)
    (out / f"{aid}.rbxm").write_bytes(root)
    print(f"[*] asset raíz {aid}: {len(root)} bytes")

    todo, done, meshes, textures = find_refs(root), set(), [], []
    print(f"[*] referencias: {todo}")
    while todo:
        rid = todo.pop(0)
        if rid in done: continue
        done.add(rid)
        try:
            d = fetch_asset(rid)
        except Exception as e:
            print(f"  ! {rid}: {e}"); continue
        if d[:8] == b"\x89PNG\r\n\x1a\n" or d[:2] == b"\xff\xd8":
            ext = "png" if d[0] == 0x89 else "jpg"
            p = out / f"texture_{rid}.{ext}"; p.write_bytes(d)
            textures.append(p); print(f"  [tex] {p.name} ({len(d)} B)")
        elif d.startswith(b"version "):
            p = out / f"mesh_{rid}.mesh"; p.write_bytes(d)
            try:
                ver, V, UV, F = parse_mesh(d)
                obj = out / f"mesh_{rid}.obj"
                write_obj(obj, f"mesh_{rid}", V, UV, F, mtl=f"mesh_{rid}.mtl")
                meshes.append(obj)
                print(f"  [mesh] {p.name} v{ver} -> {obj.name}  {len(V)} verts / {len(F)} tris")
            except Exception as e:
                print(f"  [mesh] {p.name} guardado, pero no pude convertir: {e}")
        else:
            p = out / f"sub_{rid}.rbxm"; p.write_bytes(d)
            new = [r for r in find_refs(d) if r not in done]
            print(f"  [rbxm] {p.name} -> {new}")
            todo += new

    # .mtl que enlaza la primera textura
    if meshes and textures:
        for m in meshes:
            m.with_suffix(".mtl").write_text(
                "newmtl material0\nKd 1 1 1\nd 1\nillum 2\n"
                f"map_Kd {textures[0].name}\n")
    print(f"\n[OK] {len(meshes)} malla(s), {len(textures)} textura(s) en {out}")

if __name__ == "__main__":
    main()
