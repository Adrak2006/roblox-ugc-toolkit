#!/usr/bin/env python3
"""Exporta una malla de Roblox a fbx/obj/glb aplicando una rotacion opcional en Y.
   Uso: exportar.py mesh.mesh textura.png destino/ Nombre [gradosY]"""
import sys, pathlib, shutil, numpy as np, meshconv, fbx as FBX, glb as GLB

def rotY(deg):
    a = np.deg2rad(deg)
    return np.array([[ np.cos(a), 0, np.sin(a)],
                     [ 0,         1, 0        ],
                     [-np.sin(a), 0, np.cos(a)]])

def main(mesh, tex_src, dest, name, deg=0.0):
    dest = pathlib.Path(dest); dest.mkdir(parents=True, exist_ok=True)
    R = rotY(deg)
    orig = meshconv.load
    def patched(_):
        ver, V, UV, F = orig(mesh)
        return ver, (np.asarray(V, float) @ R.T), UV, F
    meshconv.load = patched
    try:
        png = dest / f"{name}.png"
        if pathlib.Path(tex_src).resolve() != png.resolve(): shutil.copy(tex_src, png)
        FBX.build(mesh, png.name, str(dest / f"{name}.fbx"), name)
        GLB.build(mesh, str(png), str(dest / f"{name}.glb"), name)
        meshconv.write_obj(str(dest / f"{name}.obj"), *patched(mesh)[1:], tex=png.name)
        V = patched(mesh)[1]
        print(f"  rotacion aplicada: {deg:g} grados en Y")
        print(f"  bbox Z: {V[:,2].min():+.3f} .. {V[:,2].max():+.3f}")
    finally:
        meshconv.load = orig

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
         float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
