#!/usr/bin/env python3
"""Dos repintados del casco Vikingo: HUESO (paleta del craneo Wendigo) y OXIDO
   (paleta de las cadenas oxidadas). Conserva el relieve y el sombreado originales."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); import numpy as np, meshconv, ao as AO
from PIL import Image, ImageFilter
from oscurecer import fbm

LUM = np.array([.299,.587,.114])
# Uso: viking_retex.py casco.mesh textura.png  (o MESH=/TEX= en el entorno)
# Paletas: PALETA_HUESO, PALETA_OXIDO, PALETA_METAL (texturas de referencia); salida en SALIDA (.)
import os, sys
MESH = os.environ.get('MESH') or (sys.argv[1] if len(sys.argv) > 1 else 'casco.mesh')
TEX  = os.environ.get('TEX') or (sys.argv[2] if len(sys.argv) > 2 else 'textura.png')

def lum(a): return a @ LUM

# ---------------------------------------------------- capa 3D (AO + manchas)
def capa_volumen(ao_gain, blotch, under, seed=5, blob_freq=1.6):
    ver, V, UV, F = meshconv.load(MESH)
    V=np.asarray(V,float); UV=np.asarray(UV,float); F=np.asarray(F,int)
    ao, N = AO.vertex_ao(V, F, strength=1.0)
    aoA = np.clip((ao-ao.min())/(ao.max()-ao.min()+1e-9),0,1)**0.7
    undr = np.clip(-N[:,1],0,1)
    span = (V.max(0)-V.min(0)).max()
    blob = fbm(V/span, blob_freq, seed, 2)
    blob = np.clip((blob-blob.min())/(blob.max()-blob.min()+1e-9),0,1)
    blob = np.clip((blob-0.45)/0.42,0,1)
    d = np.clip(1 - ao_gain*(1-aoA) - under*undr - blotch*blob, 0.22, 1.0)
    D = AO.bake(UV, F, d, size=1024, pad=10)
    D = np.asarray(Image.fromarray((D*255).astype('uint8')).filter(
                   ImageFilter.GaussianBlur(1.5)), float)/255
    print(f"   AO por vertice: min {ao.min():.3f} media {ao.mean():.3f}")
    return np.where(D <= 0.001, 1.0, D)

# ---------------------------------------------------- LUT de paleta objetivo
def lut_percentil(px, n=256, win=0.02):
    L = lum(px); px = px[np.argsort(L)]; N = len(px)
    w = max(int(N*win), 8); lut = np.empty((n,3))
    for i in range(n):
        c = int(i/(n-1)*(N-1)); a,b = max(0,c-w), min(N,c+w+1)
        lut[i] = px[a:b].mean(0)
    k = np.ones(9)/9
    for ch in range(3):
        lut[:,ch] = np.convolve(np.pad(lut[:,ch],4,mode='edge'), k, 'valid')
    return lut

def transferir(src, lut, detail=0.85):
    L = lum(src); ref = np.sort(L.ravel())
    rank = np.searchsorted(ref, L, side='left') / max(len(ref)-1, 1)
    out = lut[np.clip((rank*255).astype(int),0,255)]
    blur = np.asarray(Image.fromarray(L.astype('uint8')).filter(
                      ImageFilter.GaussianBlur(2.0)), float)
    return np.clip(out + ((L-blur)*detail)[...,None], 0, 255)

# ---------------------------------------------------- ratio cromatico (oxido)
def lut_ratio(px, ancho=6):
    L = lum(px); ratio = np.ones((256,3))
    for i in range(256):
        sel = (L >= i-ancho) & (L <= i+ancho)
        if sel.sum() >= 60:
            c = px[sel].mean(0); ratio[i] = c/max(lum(c),1e-6)
    ok = np.where((ratio != 1).any(1))[0]
    if len(ok):
        ratio[:ok[0]] = ratio[ok[0]]; ratio[ok[-1]+1:] = ratio[ok[-1]]
    k = np.ones(21)/21
    for ch in range(3):
        ratio[:,ch] = np.convolve(np.pad(ratio[:,ch],10,mode='edge'), k, 'valid')
    return ratio

# ---------------------------------------------------- main
V = np.asarray(Image.open(TEX).convert('RGB'), float)
Lv = lum(V)

C = np.asarray(Image.open(os.environ.get('PALETA_HUESO', 'paleta_hueso.png')).convert('RGB'), float)
mxc = C.max(2); satc = np.where(mxc>0,(mxc-C.min(2))/np.maximum(mxc,1e-9),0)
craneo = C[(mxc/255>0.045) & (satc<0.45)]

O = np.asarray(Image.open(os.environ.get('PALETA_OXIDO', 'paleta_oxido.png')).convert('RGB'), float)
oxido = O[O.max(2)/255 >= 0.045]

print("[HUESO]")
Dv = capa_volumen(ao_gain=0.62, blotch=0.34, under=0.16, seed=5)
hueso = transferir(V, lut_percentil(craneo))
comp = 1 - 0.45*np.clip((lum(hueso)-150)/105, 0, None)**1.5
hueso = np.clip(hueso * (Dv*np.clip(comp,0.4,1.0))[...,None], 0, 255)
Image.fromarray(hueso.astype('uint8')).save(os.path.join(os.environ.get('SALIDA', '.'), 'casco_HUESO.png'))
print(f"   lum {Lv.mean():.1f} -> {lum(hueso).mean():.1f}   RGB medio {np.round(hueso.reshape(-1,3).mean(0),1)}")

print("[OXIDO]")
Do = capa_volumen(ao_gain=0.70, blotch=0.42, under=0.18, seed=9)
ratio = lut_ratio(oxido)
Lo = 255 * (np.clip(Lv,0,255)/255)**1.75 * 0.74        # comprime al rango real del oxido
ox = np.clip(ratio[np.clip(Lo.astype(int),0,255)] * Lo[...,None], 0, 255)
blur = np.asarray(Image.fromarray(Lv.astype('uint8')).filter(ImageFilter.GaussianBlur(2.0)), float)
ox = np.clip(ox + ((Lv-blur)*0.55)[...,None], 0, 255)   # devolver micro-relieve
ox = np.clip(ox * Do[...,None], 0, 255)
Image.fromarray(ox.astype('uint8')).save(os.path.join(os.environ.get('SALIDA', '.'), 'casco_OXIDO.png'))
print(f"   lum {Lv.mean():.1f} -> {lum(ox).mean():.1f}   RGB medio {np.round(ox.reshape(-1,3).mean(0),1)}")

# ---------------------------------------------------- version METAL (muzzle)
print("[METAL]")
Mx = np.asarray(Image.open(os.environ.get('PALETA_METAL', 'paleta_metal.png')).convert('RGB'), float)
metal = Mx[Mx.max(2)/255 >= 0.045]
Dm = capa_volumen(ao_gain=0.72, blotch=0.40, under=0.18, seed=13)
rat_m = lut_ratio(metal)
rat_m = 1 + (rat_m - 1)*1.45                          # realza el tinte de corrosion
Lm = 255 * (np.clip(Lv,0,255)/255)**1.50 * 0.82
Lm = np.clip(Lm * Dm, 0, 255)                         # AO ANTES del tinte: los huecos se corroen
mt = np.clip(rat_m[np.clip(Lm.astype(int),0,255)] * Lm[...,None], 0, 255)
blur = np.asarray(Image.fromarray(Lv.astype('uint8')).filter(ImageFilter.GaussianBlur(2.0)), float)
mt = np.clip(mt + ((Lv-blur)*0.65)[...,None], 0, 255)
Image.fromarray(mt.astype('uint8')).save(os.path.join(os.environ.get('SALIDA', '.'), 'casco_METAL.png'))
sat = lambda a: np.median(np.where(a.max(2)>0,(a.max(2)-a.min(2))/np.maximum(a.max(2),1e-9),0))
print(f"   lum {Lv.mean():.1f} -> {lum(mt).mean():.1f}   RGB medio {np.round(mt.reshape(-1,3).mean(0),1)}   sat {sat(mt):.2f}")
