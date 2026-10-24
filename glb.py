#!/usr/bin/env python3
"""Empaqueta un .mesh de Roblox + su textura PNG en un .glb autocontenido.
   Uso: glb.py in.mesh tex.png out.glb [Nombre]"""
import sys, json, struct, base64, pathlib
import numpy as np
import meshconv

def pad4(b, fill=b'\0'): return b + fill * ((4 - len(b) % 4) % 4)

def build(mesh_path, tex_path, out_path, name=None):
    ver, V, UV, F = meshconv.load(mesh_path)
    V  = np.asarray(V,  np.float32)
    UV = np.asarray(UV, np.float32)
    F  = np.asarray(F,  np.uint32)
    UV = UV.astype(np.float32)   # glTF ya usa V hacia abajo: mismo criterio que Roblox

    N = np.zeros_like(V)                                   # normales suavizadas
    tri = V[F]
    fn = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    for i in range(3): np.add.at(N, F[:,i], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    N = (N / np.where(ln < 1e-12, 1, ln)).astype(np.float32)

    png = pathlib.Path(tex_path).read_bytes()
    parts, views, accs = [], [], []
    off = 0
    def add(data, target=None):
        nonlocal off
        d = pad4(data.tobytes() if hasattr(data, 'tobytes') else data)
        parts.append(d)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(d)}
        if target: v["target"] = target
        views.append(v); off += len(d); return len(views) - 1

    vP, vN, vT = add(V, 34962), add(N, 34962), add(UV, 34962)
    vI = add(F, 34963)
    vImg = add(png)

    accs = [
      {"bufferView": vP, "componentType": 5126, "count": len(V), "type": "VEC3",
       "min": V.min(0).tolist(), "max": V.max(0).tolist()},
      {"bufferView": vN, "componentType": 5126, "count": len(V), "type": "VEC3"},
      {"bufferView": vT, "componentType": 5126, "count": len(V), "type": "VEC2"},
      {"bufferView": vI, "componentType": 5125, "count": F.size,  "type": "SCALAR"},
    ]
    nm = name or pathlib.Path(out_path).stem
    gltf = {
      "asset": {"version": "2.0", "generator": "roblox-asset-ripper"},
      "scene": 0, "scenes": [{"nodes": [0]}],
      "nodes": [{"mesh": 0, "name": nm}],
      "meshes": [{"name": nm, "primitives": [{
          "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
          "indices": 3, "material": 0}]}],
      "materials": [{"name": nm + "_mat", "doubleSided": True,
          "pbrMetallicRoughness": {
              "baseColorTexture": {"index": 0},
              "metallicFactor": 0.0, "roughnessFactor": 0.85}}],
      "textures": [{"source": 0, "sampler": 0}],
      "images": [{"bufferView": vImg, "mimeType": "image/png", "name": "diffuse"}],
      "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
      "bufferViews": views, "accessors": accs,
      "buffers": [{"byteLength": off}],
    }
    js  = pad4(json.dumps(gltf, separators=(',',':')).encode(), b' ')
    bin_ = b''.join(parts)
    glb = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
           + struct.pack("<II", len(js), 0x4E4F534A) + js
           + struct.pack("<II", len(bin_), 0x004E4942) + bin_)
    pathlib.Path(out_path).write_bytes(glb)
    print(f"  {pathlib.Path(out_path).name:38s} v{ver}  {len(V)} verts / {len(F)} tris  {len(glb)/1024:.0f} KB")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
