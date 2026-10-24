#!/usr/bin/env python3
"""Parser del formato binario .rbxm de Roblox (lo justo para leer arboles de instancias)."""
import struct, numpy as np, lz4.block

def _chunks(data):
    pos = 16 + 16
    while pos + 16 <= len(data):
        name = data[pos:pos+4]
        clen, ulen, _ = struct.unpack_from("<III", data, pos+4)
        pos += 16
        raw = data[pos:pos+(clen if clen else ulen)]
        pos += (clen if clen else ulen)
        if clen:
            raw = lz4.block.decompress(raw, uncompressed_size=ulen)
        yield name, raw
        if name == b"END\x00": break

def _str(b, o):
    n, = struct.unpack_from("<I", b, o)
    return b[o+4:o+4+n], o+4+n

def _untransp(b, o, count, width=4):
    """Deshace el entrelazado por bytes de Roblox."""
    a = np.frombuffer(b[o:o+count*width], dtype=np.uint8).reshape(width, count)
    return a.T.copy(), o + count*width

def _i32(b, o, count):
    raw, o = _untransp(b, o, count)
    u = raw.astype(np.uint32)
    v = (u[:,0]<<24)|(u[:,1]<<16)|(u[:,2]<<8)|u[:,3]
    return ((v >> 1) ^ (-(v & 1)).astype(np.uint32)).astype(np.int32), o

def _f32(b, o, count):
    raw, o = _untransp(b, o, count)
    u = raw.astype(np.uint32)
    v = (u[:,0]<<24)|(u[:,1]<<16)|(u[:,2]<<8)|u[:,3]
    bits = ((v >> 1) | (v << 31)).astype(np.uint32)
    return bits.view(np.float32) if bits.size else np.array([],np.float32), o

AXES = [(1,0,0),(0,1,0),(0,0,1),(-1,0,0),(0,-1,0),(0,0,-1)]
def orient(idv):
    v = idv - 1
    X = np.array(AXES[v // 6], float); Y = np.array(AXES[v % 6], float)
    return np.array([X, Y, np.cross(X, Y)])

def load(path):
    data = open(path, 'rb').read()
    classes, insts, props, parents = {}, {}, {}, []
    for name, b in _chunks(data):
        if name == b"INST":
            ci, = struct.unpack_from("<I", b, 0); o = 4
            cname, o = _str(b, o)
            fmt = b[o]; o += 1
            cnt, = struct.unpack_from("<I", b, o); o += 4
            refs, o = _i32(b, o, cnt)
            refs = np.cumsum(refs)
            classes[ci] = (cname.decode(), refs)
            for r in refs: insts[int(r)] = {"_class": cname.decode(), "_ref": int(r)}
        elif name == b"PROP":
            ci, = struct.unpack_from("<I", b, 0); o = 4
            pname, o = _str(b, o)
            t = b[o]; o += 1
            if ci not in classes: continue
            cname, refs = classes[ci]; n = len(refs)
            pn = pname.decode()
            vals = None
            try:
                if t == 0x01:
                    vals = []
                    for _ in range(n):
                        s, o = _str(b, o); vals.append(s.decode('utf8','replace'))
                elif t == 0x02:
                    vals = [bool(b[o+i]) for i in range(n)]; o += n
                elif t == 0x03:                      # Int32
                    vals, o = _i32(b, o, n)
                elif t == 0x04:                      # Float32
                    vals, o = _f32(b, o, n)
                elif t == 0x05:                      # Float64 (plano, sin entrelazar)
                    vals = np.frombuffer(b[o:o+8*n], '<f8').copy(); o += 8*n
                elif t == 0x0E:                      # Vector3
                    x,o = _f32(b,o,n); y,o = _f32(b,o,n); z,o = _f32(b,o,n)
                    vals = np.stack([x,y,z],1)
                elif t == 0x10:
                    rots = []
                    for _ in range(n):
                        oid = b[o]; o += 1
                        if oid == 0:
                            m = np.frombuffer(b[o:o+36], '<f4').reshape(3,3); o += 36
                        else:
                            m = orient(oid)
                        rots.append(np.array(m, float))
                    x,o = _f32(b,o,n); y,o = _f32(b,o,n); z,o = _f32(b,o,n)
                    vals = [(rots[i], np.array([x[i],y[i],z[i]])) for i in range(n)]
                elif t == 0x12:
                    raw, o = _untransp(b, o, n)
                    u = raw.astype(np.uint32)
                    vals = ((u[:,0]<<24)|(u[:,1]<<16)|(u[:,2]<<8)|u[:,3])
                elif t == 0x13:
                    v, o = _i32(b, o, n); vals = np.cumsum(v)
                else:
                    continue
            except Exception:
                continue
            for i, r in enumerate(refs):
                insts[int(r)][pn] = vals[i]
        elif name == b"PRNT":
            o = 1
            cnt, = struct.unpack_from("<I", b, o); o += 4
            ch, o = _i32(b, o, cnt); pa, o = _i32(b, o, cnt)
            parents = list(zip(np.cumsum(ch), np.cumsum(pa)))
    for c, p in parents:
        if int(c) in insts: insts[int(c)]["_parent"] = int(p)
    return insts
