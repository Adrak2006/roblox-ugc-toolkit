#!/usr/bin/env python3
"""Oscurecido estilo Wendigo: cada isla de hueso se ensucia hacia su contorno
   (medido del craneo: bordes un 37% mas oscuros), mas AO y manchas de ruido 3D."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); import numpy as np, meshconv, ao as AO
from PIL import Image, ImageFilter
from scipy.ndimage import distance_transform_edt, label
from oscurecer import fbm

LUM = np.array([.299,.587,.114])

def rim_map(bone, inset=0.45, k=1.15):
    """Profundidad relativa dentro de cada isla: 0 en el contorno, 1 en el nucleo."""
    lab, n = label(bone)
    rel = np.zeros(bone.shape)
    d = distance_transform_edt(bone)
    for i in range(1, n+1):
        m = lab == i
        if m.sum() < 40: continue
        mx = d[m].max()
        if mx < 1: continue
        rel[m] = np.clip(d[m]/(mx*inset), 0, 1)
    t = np.clip(rel, 0, 1)
    return t*t*(3-2*t)**1 if False else (1-(1-t)**k)      # suavizado hacia el nucleo

def build(out_png, rim_dark, ao_gain, blotch, under, hi_comp, floor_=0.30, seed=11,
          mesh=None, tex=None):
    ver, V, UV, F = meshconv.load(mesh)
    V=np.asarray(V,float); UV=np.asarray(UV,float); F=np.asarray(F,int)

    # --- capa 3D: AO + cara inferior + manchas (continuas entre costuras)
    ao, N = AO.vertex_ao(V, F, strength=1.0)
    aoA = np.clip((ao-ao.min())/(ao.max()-ao.min()+1e-9),0,1)**0.7
    undr = np.clip(-N[:,1],0,1)
    span = (V.max(0)-V.min(0)).max()
    blob = fbm(V/span, 1.3, seed, 2)
    blob = np.clip((blob-blob.min())/(blob.max()-blob.min()+1e-9),0,1)
    blob = np.clip((blob-0.45)/0.42,0,1)
    d3 = np.clip(1 - ao_gain*(1-aoA) - under*undr - blotch*blob, 0.25, 1.0)
    D3 = AO.bake(UV, F, d3, size=1024, pad=8)
    D3 = np.where(D3 <= 0.001, 1.0, D3)

    # --- capa 2D: oscurecido por contorno de isla
    T = np.asarray(Image.open(tex).convert('RGB'), float)
    hw = T.max(2); sw = np.where(hw>0,(hw-T.min(2))/np.maximum(hw,1e-9),0)
    bg = hw/255 < 0.045
    memb = (~bg) & (sw > 0.6)
    bone = (~bg) & (~memb)
    rel = rim_map(bone)
    D2 = np.where(bone, 1 - rim_dark*(1-rel), 1.0)
    D2 = np.asarray(Image.fromarray((D2*255).astype('uint8')).filter(
                    ImageFilter.GaussianBlur(2.5)), float)/255
    D2 = np.where(bone, D2, 1.0)

    L = T@LUM
    comp = 1 - hi_comp*np.clip((L-150)/105, 0, None)**1.5
    fac = np.clip(D3*D2*np.clip(comp,0.4,1.0), floor_, 1.0)

    out = T.copy()
    out[bone] = np.clip(T[bone]*fac[bone][:,None], 0, 255)
    Image.fromarray(out.astype('uint8')).save(out_png)

    o=T[bone]@LUM; b=out[bone]@LUM
    d=distance_transform_edt(bone)
    edge=bone&(d<3); core=bone&(d>=6)&(d<25)
    print(f"  {out_png.split('/')[-1]:26s} lum {o.mean():5.1f}->{b.mean():5.1f}  "
          f"borde {b[edge[bone]].mean() if edge.sum() else 0:5.1f} vs nucleo {b[core[bone]].mean():5.1f}  "
          f"(craneo: 74.8 vs 118)")

if __name__ == "__main__":
    # Uso: oscurecer2.py malla.mesh textura.png carpeta_salida/
    import sys
    M, T, O = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/')
    build(O + '/textura_C.png', rim_dark=0.40, ao_gain=0.55, blotch=0.30, under=0.14, hi_comp=0.40, floor_=0.34, mesh=M, tex=T)
    build(O + '/textura_D.png', rim_dark=0.56, ao_gain=0.78, blotch=0.46, under=0.20, hi_comp=0.58, floor_=0.26, mesh=M, tex=T)
    build(O + '/textura_E.png', rim_dark=0.70, ao_gain=1.00, blotch=0.62, under=0.26, hi_comp=0.72, floor_=0.20, mesh=M, tex=T)
