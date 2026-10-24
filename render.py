#!/usr/bin/env python3
"""Render por software de un .mesh de Roblox con su textura. Uso: render.py mesh tex out.png [angulo]"""
import sys, numpy as np
from PIL import Image
import meshconv

def render(mesh, texp, outp, ang_deg=40, W=760, H=760, bg=(16,16,20)):
    ver, V, UV, F = meshconv.load(mesh)
    V = np.asarray(V, float); UV = np.asarray(UV, float); F = np.asarray(F, int)
    tex = np.asarray(Image.open(texp).convert('RGB'), float); th, tw = tex.shape[:2]
    a = np.deg2rad(ang_deg)
    R = np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    P = V @ R.T
    mn, mx = P[:,:2].min(0), P[:,:2].max(0); c = (mn+mx)/2
    s = 0.88*min(W,H)/(mx-mn).max()
    x = (P[:,0]-c[0])*s + W/2; y = H/2 - (P[:,1]-c[1])*s; z = P[:,2]
    img = np.tile(np.array(bg,float), (H,W,1)); zb = np.full((H,W), -1e9)
    for i0,i1,i2 in F:
        xs,ys,zs = x[[i0,i1,i2]], y[[i0,i1,i2]], z[[i0,i1,i2]]
        x0,x1 = int(max(0,np.floor(xs.min()))), int(min(W-1,np.ceil(xs.max())))
        y0,y1 = int(max(0,np.floor(ys.min()))), int(min(H-1,np.ceil(ys.max())))
        if x1<x0 or y1<y0: continue
        d = (ys[1]-ys[2])*(xs[0]-xs[2]) + (xs[2]-xs[1])*(ys[0]-ys[2])
        if abs(d) < 1e-9: continue
        gx,gy = np.meshgrid(np.arange(x0,x1+1)+.5, np.arange(y0,y1+1)+.5)
        l0 = ((ys[1]-ys[2])*(gx-xs[2]) + (xs[2]-xs[1])*(gy-ys[2]))/d
        l1 = ((ys[2]-ys[0])*(gx-xs[2]) + (xs[0]-xs[2])*(gy-ys[2]))/d
        l2 = 1-l0-l1
        m = (l0>=0)&(l1>=0)&(l2>=0)
        if not m.any(): continue
        zz = l0*zs[0]+l1*zs[1]+l2*zs[2]
        sub = zb[y0:y1+1, x0:x1+1]; upd = m & (zz > sub)
        if not upd.any(): continue
        uu = l0*UV[i0,0]+l1*UV[i1,0]+l2*UV[i2,0]
        vv = l0*UV[i0,1]+l1*UV[i1,1]+l2*UV[i2,1]
        col = tex[np.clip((vv*th).astype(int),0,th-1), np.clip((uu*tw).astype(int),0,tw-1)]
        n = np.cross([xs[1]-xs[0],ys[1]-ys[0],zs[1]-zs[0]], [xs[2]-xs[0],ys[2]-ys[0],zs[2]-zs[0]])
        n = n/(np.linalg.norm(n)+1e-9)
        sh = 0.42 + 0.58*abs(n[2])
        sub[upd] = zz[upd]; img[y0:y1+1, x0:x1+1][upd] = col[upd]*sh
    Image.fromarray(img.clip(0,255).astype('uint8')).save(outp)
    return outp

if __name__ == "__main__":
    print("->", render(sys.argv[1], sys.argv[2], sys.argv[3],
                       float(sys.argv[4]) if len(sys.argv) > 4 else 40))
