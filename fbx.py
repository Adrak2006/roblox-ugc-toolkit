#!/usr/bin/env python3
"""Exporta un .mesh de Roblox a FBX ASCII 7.4 listo para el importador 3D de Studio.
   Uso: fbx.py in.mesh textura.png salida.fbx [Nombre]"""
import sys, pathlib, numpy as np, meshconv

TPL = """; FBX 7.4.0 project file
FBXHeaderExtension:  {{
    FBXHeaderVersion: 1003
    FBXVersion: 7400
    Creator: "roblox-asset-ripper"
}}
GlobalSettings:  {{
    Version: 1000
    Properties70:  {{
        P: "UpAxis", "int", "Integer", "",1
        P: "UpAxisSign", "int", "Integer", "",1
        P: "FrontAxis", "int", "Integer", "",2
        P: "FrontAxisSign", "int", "Integer", "",1
        P: "CoordAxis", "int", "Integer", "",0
        P: "CoordAxisSign", "int", "Integer", "",1
        P: "OriginalUpAxis", "int", "Integer", "",1
        P: "UnitScaleFactor", "double", "Number", "",1
        P: "OriginalUnitScaleFactor", "double", "Number", "",1
    }}
}}
Definitions:  {{
    Version: 100
    Count: 4
    ObjectType: "Geometry"  {{
        Count: 1
    }}
    ObjectType: "Model"  {{
        Count: 1
    }}
    ObjectType: "Material"  {{
        Count: 1
    }}
    ObjectType: "Texture"  {{
        Count: 1
    }}
    ObjectType: "Video"  {{
        Count: 1
    }}
}}
Objects:  {{
    Geometry: 1000000, "Geometry::{name}", "Mesh" {{
        Vertices: *{nv} {{
            a: {verts}
        }}
        PolygonVertexIndex: *{ni} {{
            a: {idx}
        }}
        GeometryVersion: 124
        LayerElementNormal: 0 {{
            Version: 102
            Name: ""
            MappingInformationType: "ByPolygonVertex"
            ReferenceInformationType: "Direct"
            Normals: *{nn} {{
                a: {norms}
            }}
        }}
        LayerElementUV: 0 {{
            Version: 101
            Name: "UVMap"
            MappingInformationType: "ByPolygonVertex"
            ReferenceInformationType: "IndexToDirect"
            UV: *{nuv} {{
                a: {uvs}
            }}
            UVIndex: *{ni} {{
                a: {uvidx}
            }}
        }}
        LayerElementMaterial: 0 {{
            Version: 101
            Name: ""
            MappingInformationType: "AllSame"
            ReferenceInformationType: "IndexToDirect"
            Materials: *1 {{
                a: 0
            }}
        }}
        Layer: 0 {{
            Version: 100
            LayerElement:  {{
                Type: "LayerElementNormal"
                TypedIndex: 0
            }}
            LayerElement:  {{
                Type: "LayerElementUV"
                TypedIndex: 0
            }}
            LayerElement:  {{
                Type: "LayerElementMaterial"
                TypedIndex: 0
            }}
        }}
    }}
    Model: 2000000, "Model::{name}", "Mesh" {{
        Version: 232
        Properties70:  {{
            P: "ScalingMax", "Vector3D", "Vector", "",0,0,0
            P: "DefaultAttributeIndex", "int", "Integer", "",0
        }}
        Shading: T
        Culling: "CullingOff"
    }}
    Material: 3000000, "Material::{name}_mat", "" {{
        Version: 102
        ShadingModel: "phong"
        MultiLayer: 0
        Properties70:  {{
            P: "DiffuseColor", "Color", "", "A",1,1,1
            P: "SpecularColor", "Color", "", "A",0,0,0
            P: "Shininess", "double", "Number", "",0
        }}
    }}
    Texture: 4000000, "Texture::diffuse", "" {{
        Type: "TextureVideoClip"
        Version: 202
        TextureName: "Texture::diffuse"
        Media: "Video::diffuse"
        FileName: "{tex}"
        RelativeFilename: "{tex}"
        ModelUVTranslation: 0,0
        ModelUVScaling: 1,1
        Texture_Alpha_Source: "None"
        Cropping: 0,0,0,0
    }}
    Video: 5000000, "Video::diffuse", "Clip" {{
        Type: "Clip"
        Properties70:  {{
            P: "Path", "KString", "XRefUrl", "", "{tex}"
        }}
        UseMipMap: 0
        Filename: "{tex}"
        RelativeFilename: "{tex}"
    }}
}}
Connections:  {{
    C: "OO",2000000,0
    C: "OO",1000000,2000000
    C: "OO",3000000,2000000
    C: "OP",4000000,3000000, "DiffuseColor"
    C: "OO",5000000,4000000
}}
"""

def build(mesh_path, tex_name, out_path, name=None):
    ver, V, UV, F = meshconv.load(mesh_path)
    V  = np.asarray(V, float)
    UV = np.asarray(UV, float)
    F  = np.asarray(F, int)
    UV = np.column_stack([UV[:,0], 1.0 - UV[:,1]])        # FBX: V hacia arriba, como OBJ

    N = np.zeros_like(V)                                   # normales suavizadas
    tri = V[F]
    fn = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    for i in range(3): np.add.at(N, F[:,i], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    N = N / np.where(ln < 1e-12, 1, ln)

    idx = F.copy(); idx[:,2] = -idx[:,2] - 1               # FBX cierra el poligono negando el ultimo
    pvi = idx.reshape(-1)
    pv  = F.reshape(-1)                                    # indice de vertice por esquina

    j = lambda a, f="%.6f": ",".join(f % x for x in a)
    body = TPL.format(
        name=name or pathlib.Path(out_path).stem,
        tex=tex_name,
        nv=V.size,   verts=j(V.reshape(-1)),
        ni=pvi.size, idx=",".join(str(int(x)) for x in pvi),
        nn=pv.size*3, norms=j(N[pv].reshape(-1)),
        nuv=UV.size, uvs=j(UV.reshape(-1)),
        uvidx=",".join(str(int(x)) for x in pv),
    )
    pathlib.Path(out_path).write_text(body)
    print(f"  {pathlib.Path(out_path).name:34s} v{ver}  {len(V)} verts / {len(F)} tris  "
          f"{pathlib.Path(out_path).stat().st_size/1024:.0f} KB")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
