#!/usr/bin/env python3
"""Oclusion ambiental por vertice (form-factor con los triangulos como emisores)
   y horneado al espacio UV.  Uso: ao.py mesh.mesh salida_ao.png"""
import sys, numpy as np, meshconv
from PIL import Image, ImageFilter

def vertex_ao(V, F, strength=1.0):
    V = np.asarray(V, float); F = np.asarray(F, int)
    tri = V[F]
    c  = tri.mean(1)                                     # centroides
    cr = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    area = np.linalg.norm(cr, axis=1) * 0.5
    fn = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)

    N = np.zeros_like(V)                                 # normales de vertice
    for i in range(3): np.add.at(N, F[:,i], cr)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)

    occ = np.zeros(len(V))
    CH = 256
    for s in range(0, len(V), CH):
        P = V[s:s+CH]; Nn = N[s:s+CH]
        d = c[None,:,:] - P[:,None,:]                    # (chunk, tris, 3)
        dist2 = (d*d).sum(2) + 1e-9
        dist = np.sqrt(dist2)
        u = d / dist[...,None]
        cos_r = np.einsum('ck,ijk->ij', np.eye(3), u @ np.eye(3))  # placeholder
        cos_r = (u * Nn[:,None,:]).sum(2)                # coseno en el receptor
        cos_e = (-u * fn[None,:,:]).sum(2)               # coseno en el emisor
        w = np.clip(cos_r,0,None) * np.clip(cos_e,0,None) * area[None,:]
        occ[s:s+CH] = (w / (np.pi*dist2 + area[None,:])).sum(1)
    ao = 1.0 / (1.0 + strength*occ)
    return np.clip(ao, 0, 1), N

def bake(UV, F, ao, size=1024, pad=6):
    """Rasteriza la AO en el atlas UV, con dilatacion en los bordes de isla."""
    UV = np.asarray(UV, float); F = np.asarray(F, int)
    img = np.zeros((size,size)); cov = np.zeros((size,size), bool)
    x = UV[:,0]*size; y = UV[:,1]*size
    for a,b,cc in F:
        xs,ys = x[[a,b,cc]], y[[a,b,cc]]
        x0,x1 = int(max(0,np.floor(xs.min()))), int(min(size-1,np.ceil(xs.max())))
        y0,y1 = int(max(0,np.floor(ys.min()))), int(min(size-1,np.ceil(ys.max())))
        if x1<x0 or y1<y0: continue
        d = (ys[1]-ys[2])*(xs[0]-xs[2]) + (xs[2]-xs[1])*(ys[0]-ys[2])
        if abs(d)<1e-9: continue
        gx,gy = np.meshgrid(np.arange(x0,x1+1)+.5, np.arange(y0,y1+1)+.5)
        l0 = ((ys[1]-ys[2])*(gx-xs[2]) + (xs[2]-xs[1])*(gy-ys[2]))/d
        l1 = ((ys[2]-ys[0])*(gx-xs[2]) + (xs[0]-xs[2])*(gy-ys[2]))/d
        l2 = 1-l0-l1
        m = (l0>=-0.002)&(l1>=-0.002)&(l2>=-0.002)
        if not m.any(): continue
        val = l0*ao[a] + l1*ao[b] + l2*ao[cc]
        sl = (slice(y0,y1+1), slice(x0,x1+1))
        img[sl][m] = val[m]; cov[sl][m] = True
    for _ in range(pad):                                  # dilatar hacia fuera
        f = np.asarray(Image.fromarray((img*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)), float)/255
        img = np.where(cov, img, f)
        cov |= (f > 0)
    return img

if __name__ == "__main__":
    ver, V, UV, F = meshconv.load(sys.argv[1])
    ao, N = vertex_ao(V, F, strength=1.0)
    print(f"  AO por vertice: min {ao.min():.3f}  media {ao.mean():.3f}  max {ao.max():.3f}")
    img = bake(UV, F, ao)
    Image.fromarray((np.clip(img,0,1)*255).astype('uint8')).save(sys.argv[2])
    print(f"  horneada -> {sys.argv[2]}")
