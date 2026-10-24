# Roblox UGC Toolkit

Herramientas de Python para trabajar con **mallas y accesorios de Roblox** fuera de Studio:
leer cualquier `.mesh` (v1 a **v7 con Draco**), exportar a OBJ/GLB/FBX listos para Studio,
renderizar, hornear oclusión ambiental, repintar texturas respetando el relieve y montar el
accesorio con el *Attachment* exacto. Con esta cadena se hicieron accesorios UGC que Roblox
aprobó.

*English summary below.*

## Herramientas

| Script | Qué hace |
|---|---|
| `meshconv.py` | `.mesh` v1–v7 → `.obj` + `.mtl` (v7 = contenedor `COREMESH` con geometría Google Draco) |
| `mesh7.py` | Conversor mínimo solo para v7.00 |
| `glb.py` | `.mesh` + textura → `.glb` autocontenido |
| `fbx.py` | `.mesh` → **FBX ASCII 7.4** que el importador 3D de Studio acepta |
| `exportar.py` / `exportar2.py` | Exportan a fbx/obj/glb aplicando giro en Y y la `Scale` del `SpecialMesh` |
| `render.py` | Render por software (numpy) de la malla con su textura, sin GPU |
| `ao.py` | Oclusión ambiental por vértice horneada a una textura en espacio UV |
| `rbxm.py` | Parser del formato binario `.rbxm` (árbol de instancias y propiedades: CFrames, Scale…) |
| `accesorio.py` | Genera un `.rbxmx` con el Accessory montado (Handle + SpecialMesh + Attachment) |
| `rbxrip.py` | Descarga un asset del catálogo (accesorio o modelo) y extrae sus mallas y texturas |
| `studio/montar_accesorio.lua` | Lo mismo que `accesorio.py`, para pegar en la barra de comandos de Studio |
| `ejemplos/` | Recetas de repintado reales (oscurecer hueso, paleta de otra textura, óxido/metal) |

## Instalar

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Uso típico

```bash
# 1. Descargar un asset (necesita tu cookie .ROBLOSECURITY: assetdelivery ya no sirve sin sesión)
ROBLOSECURITY='...' python3 rbxrip.py 1234567890 trabajo/

# 2. Verlo y convertirlo
python3 render.py trabajo/mesh_XXXX.mesh trabajo/textura.png vista.png 30
python3 glb.py   trabajo/mesh_XXXX.mesh trabajo/textura.png modelo.glb
python3 fbx.py   trabajo/mesh_XXXX.mesh trabajo/textura.png modelo.fbx MiModelo

# 3. Repintar (ejemplos) y subir a Studio. Luego montar el accesorio con la CFrame original
python3 -c "import rbxm; print(rbxm.__doc__)"   # rbxm.py se usa como librería: lee el Attachment y la Scale del .rbxm
```

⚠️ **La cookie `.ROBLOSECURITY` da acceso completo a tu cuenta.** Pásala solo por variable de
entorno, nunca la guardes en el repo ni la compartas.

## Lo que costó descubrir

- **Mallas v7.00** = contenedor `COREMESH` + geometría en **Draco** (chunks `DRACO` y `LODS`).
  Los parsers clásicos no las leen; hace falta `DracoPy`. Las v4.xx siguen siendo el binario de
  siempre (cabecera de 24 B, vértice de 40 B, LOD0 = `faces[lods[0]:lods[1]]`).
- **Eje V de las UV**: la fila de textura correcta es `v*h`. En OBJ se escribe `vt = 1-v`; en glTF,
  `v` tal cual.
- **Studio gira el FBX 180° en yaw** al importarlo (el FBX declara frente +Z y Roblox usa −Z): hay
  que exportarlo **pre-girado 180°**.
- **`SpecialMesh.Scale` puede no ser uniforme**: hay que hornear la escala en los vértices al exportar.
- **`assets-thumbnail-3d`** devuelve el OBJ + MTL + textura que Roblox usa internamente. Es la
  mejor referencia para validar malla, UVs y orientación.
- **assimp trata `;` como comentario** en FBX ASCII.
- **F3D no detecta FBX ASCII** por la firma: hace falta una config que fuerce el lector FBX.

## Uso responsable

Roblox solo acepta UGC **original** o con derechos: subir como tuyo el trabajo de otro creador
viola sus normas y sus derechos de autor, y te pueden quitar los ítems o la cuenta. Usa
`rbxrip.py` para estudiar formatos, hacer copias de seguridad de **tus** assets o sacar
referencias, no para resubir el trabajo de otros.

## English summary

Python tools for **Roblox meshes and accessories** outside Studio: read any `.mesh` (v1–v7,
including Draco-compressed v7), export OBJ/GLB/FBX ready for Studio's importer (handles the 180°
yaw flip and non-uniform SpecialMesh scale), software render, bake AO, recolor textures while
keeping relief, parse binary `.rbxm`, build accessories with exact attachments, and download
catalog assets (`rbxrip.py`, needs your `.ROBLOSECURITY` cookie via env var).

## Licencia

MIT (ver `LICENSE`). No está afiliado a Roblox Corporation.
