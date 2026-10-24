#!/usr/bin/env python3
"""Anade zonas oscurecidas a gran escala al hueso de las alas, al estilo del craneo Wendigo.
   Combina: oclusion ambiental + cara inferior + manchas de ruido 3D (sin costuras)."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); import sys, numpy as np, meshconv, ao as AO
from PIL import Image, ImageFilter

LUM = np.array([.299,.587,.114])

def value_noise_3d(P, freq, seed):
    """Ruido de valor trilineal evaluado en puntos 3D -> continuo entre islas UV."""
    rs = np.random.RandomState(seed)
    G = 32
    grid = rs.rand(G,G,G)
    q = P*freq
    i = np.floor(q).astype(int); f = q - i
    f = f*f*(3-2*f)                                   # smoothstep
    i = i % G
    ip = (i+1) % G
    def g(a,b,c): return grid[a[:,0],b[:,1],c[:,2]]
    c000=g(i,i,i);   c100=g(ip,i,i);  c010=g(i,ip,i);  c110=g(ip,ip,i)
    c001=g(i,i,ip);  c101=g(ip,i,ip); c011=g(i,ip,ip); c111=g(ip,ip,ip)
    x00=c000+(c100-c000)*f[:,0]; x10=c010+(c110-c010)*f[:,0]
    x01=c001+(c101-c001)*f[:,0]; x11=c011+(c111-c011)*f[:,0]
    y0=x00+(x10-x00)*f[:,1];     y1=x01+(x11-x01)*f[:,1]
    return y0+(y1-y0)*f[:,2]

def fbm(P, base_freq, seed, octaves=3):
    out = np.zeros(len(P)); amp = 1.0; tot = 0.0
    for o in range(octaves):
        out += amp*value_noise_3d(P, base_freq*(2**o), seed+o*17)
        tot += amp; amp *= 0.5
    return out/tot

def build(mesh, tex_in, out_png, ao_gain, blotch, under, floor_, hi_comp, seed=7,
          blob_freq=1.5, blob_oct=2, root=0.0):
    ver, V, UV, F = meshconv.load(mesh)
    V=np.asarray(V,float); UV=np.asarray(UV,float); F=np.asarray(F,int)
    ao, N = AO.vertex_ao(V, F, strength=1.0)

    aoA   = np.clip((ao - ao.min())/(ao.max()-ao.min()+1e-9), 0, 1)   # normalizar el rango util
    aoA   = aoA**0.7
    undr  = np.clip(-N[:,1], 0, 1)                                    # cara inferior
    span  = V.max(0)-V.min(0)
    blob  = fbm(V/span.max(), blob_freq, seed, blob_oct)
    blob  = np.clip((blob-blob.min())/(blob.max()-blob.min()+1e-9), 0, 1)
    blob  = np.clip((blob-0.42)/0.45, 0, 1)                           # solo la mitad alta => manchas

    # gradiente hacia la raiz del ala / el eje central: lo interior se ensucia mas
    cen  = V - (V.max(0)+V.min(0))/2
    rad  = np.linalg.norm(cen[:,[0,1]], axis=1); rad /= rad.max()+1e-9
    inner= np.clip(1.0 - rad/0.75, 0, 1)**1.3
    dark = (1.0 - ao_gain*(1-aoA) - under*undr - blotch*blob - root*inner)
    dark = np.clip(dark, floor_, 1.0)

    Dmap = AO.bake(UV, F, dark, size=1024, pad=8)
    Dmap = np.asarray(Image.fromarray((Dmap*255).astype('uint8')).filter(
                      ImageFilter.GaussianBlur(1.2)), float)/255
    Dmap = np.where(Dmap <= 0.001, 1.0, Dmap)

    T = np.asarray(Image.open(tex_in).convert('RGB'), float)
    hw = T.max(2); sw = np.where(hw>0,(hw-T.min(2))/np.maximum(hw,1e-9),0)
    bg   = hw/255 < 0.045
    memb = (~bg) & (sw > 0.6)
    bone = (~bg) & (~memb)

    out = T.copy()
    L = T@LUM
    comp = 1 - hi_comp*np.clip((L-150)/105, 0, None)**1.5     # comprimir realces
    fac  = Dmap * np.clip(comp, 0.4, 1.0)
    out[bone] = np.clip(T[bone] * fac[bone][:,None], 0, 255)
    out[memb] = T[memb]                                               # rojo intacto
    out[bg]   = T[bg]
    Image.fromarray(out.astype('uint8')).save(out_png)
    b = out[bone]@LUM; o = T[bone]@LUM
    print(f"  {out_png.split('/')[-1]:34s} lum hueso {o.mean():5.1f} -> {b.mean():5.1f}   "
          f"p90 {np.percentile(o,90):5.1f} -> {np.percentile(b,90):5.1f}   "
          f"<90: {(o<90).mean()*100:4.1f}% -> {(b<90).mean()*100:4.1f}%")

def gen():
    # Uso: oscurecer.py malla.mesh textura.png carpeta_salida/
    M, T, O = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/')
    build(M,T,O+'/textura_C.png', ao_gain=0.75, blotch=0.42, under=0.18, floor_=0.34,
          hi_comp=0.45, blob_freq=1.4, blob_oct=2, root=0.16, seed=11)
    build(M,T,O+'/textura_D.png', ao_gain=1.00, blotch=0.60, under=0.26, floor_=0.24,
          hi_comp=0.60, blob_freq=1.1, blob_oct=2, root=0.24, seed=11)

if __name__ == "__main__":
    gen()
