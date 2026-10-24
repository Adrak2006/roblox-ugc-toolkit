#!/usr/bin/env python3
"""Reviste la textura de las alas con la paleta de la mascara Wendigo:
   membrana roja -> rojo del pentagrama, hueso amarillento -> hueso del craneo."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); import numpy as np
from PIL import Image, ImageFilter

LUM = np.array([0.299, 0.587, 0.114])
def lum(a): return a @ LUM
def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t*t*(3 - 2*t)

def hsv_sv(a):
    mx = a.max(2); mn = a.min(2)
    return np.where(mx > 0, (mx - mn)/np.maximum(mx, 1e-9), 0), mx/255.0

def hue(a):
    r,g,b = a[...,0], a[...,1], a[...,2]
    mx, mn = a.max(2), a.min(2); d = np.maximum(mx-mn, 1e-9)
    h = np.zeros_like(mx)
    i = mx==r; h[i] = ((g-b)[i]/d[i]) % 6
    i = (mx==g)&~ (mx==r); h[i] = ((b-r)[i]/d[i]) + 2
    i = (mx==b)&~((mx==r)|(mx==g)); h[i] = ((r-g)[i]/d[i]) + 4
    return h*60

def build_lut(px, n=256, win=0.02):
    """LUT de 256 pasos: percentil de luminancia -> color medio del objetivo ahi."""
    L = lum(px); order = np.argsort(L); px = px[order]; N = len(px)
    w = max(int(N*win), 8); lut = np.empty((n,3))
    for i in range(n):
        c = int(i/(n-1)*(N-1)); a, b = max(0, c-w), min(N, c+w+1)
        lut[i] = px[a:b].mean(0)
    k = np.ones(9)/9                                    # suavizado del LUT
    for c in range(3):
        lut[:,c] = np.convolve(np.pad(lut[:,c], 4, mode='edge'), k, 'valid')
    return lut

def transfer(src, mask, lut, detail_gain=0.85):
    """Mapea cada pixel de src[mask] por su percentil de luminancia dentro de la region."""
    L = lum(src)
    ref = np.sort(L[mask])
    rank = np.searchsorted(ref, L, side='left') / max(len(ref)-1, 1)
    idx = np.clip((rank*255).astype(int), 0, 255)
    out = lut[idx]
    blur = np.asarray(Image.fromarray(L.astype('uint8')).filter(
        ImageFilter.GaussianBlur(2.0)), float)          # reinyectar micro-detalle
    out += ((L - blur) * detail_gain)[..., None]
    return np.clip(out, 0, 255)

# ---------------------------------------------------------------- fuentes
# Uso: retex.py textura_alas.png textura_mascara.png carpeta_salida/
import sys
ENT, MASC, SAL = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/')
W = np.asarray(Image.open(ENT).convert('RGB'), float)
M = np.asarray(Image.open(MASC).convert('RGB'), float)

sw, vw = hsv_sv(W); hw = hue(W)
sm, vm = hsv_sv(M); hm = hue(M)

bg = vw < 0.045                                          # fondo negro del atlas: intacto
ang = np.minimum(hw, 360-hw)                             # distancia angular al rojo
w_memb = smoothstep(30-ang, 0, 12) * smoothstep(sw, 0.55, 0.78) * (~bg)
w_bone = (1.0 - w_memb) * (~bg)

# regiones objetivo de la mascara
r,g,b = M[...,0], M[...,1], M[...,2]
penta = (r > 55) & (r > g*2.2) & (r > b*2.2) & (sm > 0.7)
skull = (vm > 0.045) & (sm < 0.45) & ~penta

lut_red  = build_lut(M[penta])
lut_bone = build_lut(M[skull])

out = W.copy()
out = out*(1-w_bone[...,None]) + transfer(W, w_bone > 0.5, lut_bone)*w_bone[...,None]
out[bg] = W[bg]
out[w_memb > 0.5] = W[w_memb > 0.5]          # membrana roja: SIN TOCAR
Image.fromarray(np.clip(out,0,255).astype('uint8')).save(SAL + '/textura_repintada.png')

print("hueso %.1f%% del atlas | membrana intacta %.1f%% | fondo %.1f%%" % (
    (w_bone>0.5).mean()*100, (w_memb>0.5).mean()*100, bg.mean()*100))
m = w_bone > 0.5
print("  hueso    antes %s  ->  despues %s" % (np.round(W[m].mean(0),1), np.round(out[m].mean(0),1)))
mm = w_memb > 0.5
print("  membrana antes %s  ->  despues %s  (identica: %s)" % (
    np.round(W[mm].mean(0),1), np.round(out[mm].mean(0),1),
    np.array_equal(W[mm], out[mm])))

# ---------- variante B: cromaticidad del craneo, luminancia original de las alas
Ls = lum(M[skull]); Cs = M[skull]
ratio = np.ones((256,3))
for i in range(256):
    sel = (Ls >= i-6) & (Ls <= i+6)
    if sel.sum() >= 40:
        c = Cs[sel].mean(0); ratio[i] = c / max(lum(c), 1e-6)
valid = np.where((ratio != 1).any(1))[0]
if len(valid):                                   # rellenar extremos sin muestras
    ratio[:valid[0]] = ratio[valid[0]]; ratio[valid[-1]+1:] = ratio[valid[-1]]
k = np.ones(15)/15
for c in range(3):
    ratio[:,c] = np.convolve(np.pad(ratio[:,c], 7, mode='edge'), k, 'valid')

Lw = lum(W)
altB = W.copy()
tinted = np.clip(ratio[np.clip(Lw.astype(int), 0, 255)] * Lw[..., None], 0, 255)
altB = altB*(1-w_bone[...,None]) + tinted*w_bone[...,None]
altB[bg] = W[bg]; altB[w_memb > 0.5] = W[w_memb > 0.5]
Image.fromarray(np.clip(altB,0,255).astype('uint8')).save(SAL + '/textura_repintada_B.png')
m = w_bone > 0.5
print("  variante B hueso: %s (lum %.1f, original lum %.1f)" % (
    np.round(altB[m].mean(0),1), lum(altB[m].mean(0)), lum(W[m].mean(0))))
