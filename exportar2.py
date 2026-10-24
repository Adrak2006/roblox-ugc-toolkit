#!/usr/bin/env python3
"""Exporta una malla de Roblox a fbx/obj/glb aplicando la Scale del SpecialMesh
   y el giro de 180 en Y que compensa el importador de Studio."""
import pathlib, shutil, numpy as np, meshconv, fbx as FBX, glb as GLB

def exportar(mesh, tex_src, dest, name, scale=(1,1,1), degY=180.0):
    dest = pathlib.Path(dest); dest.mkdir(parents=True, exist_ok=True)
    a = np.deg2rad(degY)
    R = np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    S = np.diag(np.asarray(scale, float))
    M = R @ S                                    # escalar y luego girar
    orig = meshconv.load
    def patched(_):
        ver, V, UV, F = orig(mesh)
        return ver, (np.asarray(V, float) @ M.T), UV, F
    meshconv.load = patched
    try:
        png = dest / f"{name}.png"
        if pathlib.Path(tex_src).resolve() != png.resolve(): shutil.copy(tex_src, png)
        FBX.build(mesh, png.name, str(dest / f"{name}.fbx"), name)
        GLB.build(mesh, str(png), str(dest / f"{name}.glb"), name)
        meshconv.write_obj(str(dest / f"{name}.obj"), *patched(mesh)[1:], tex=png.name)
        V = patched(mesh)[1]
        print(f"   tamano final: {np.round(V.max(0)-V.min(0),4)} studs   (giro {degY:g}, escala {np.round(scale,5)})")
    finally:
        meshconv.load = orig
