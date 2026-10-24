#!/usr/bin/env python3
"""Genera un .rbxmx (modelo XML de Roblox) con el Accessory ya montado:
   Handle + SpecialMesh + BodyBackAttachment en la CFrame exacta del original."""
import sys

CF = (0.0, 0.21148, -1.0476)      # por defecto: BodyBackAttachment de las alas

def cframe(name, p):
    return f"""        <CoordinateFrame name="{name}">
          <X>{p[0]}</X><Y>{p[1]}</Y><Z>{p[2]}</Z>
          <R00>1</R00><R01>0</R01><R02>0</R02>
          <R10>0</R10><R11>1</R11><R12>0</R12>
          <R20>0</R20><R21>0</R21><R22>1</R22>
        </CoordinateFrame>"""

def build(mesh_id, texture_id, name, out, att="BodyBackAttachment", cf=None, atype=7,
          scale=(1,1,1), size=(1,1,1)):
    p = cf if cf else CF
    sx,sy,sz = scale; hx,hy,hz = size
    xml = f"""<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">
  <External>null</External>
  <External>nil</External>
  <Item class="Accessory" referent="RBX0">
    <Properties>
      <string name="Name">{name}</string>
      <token name="AccessoryType">{atype}</token>
{cframe("AttachmentPoint", p)}
    </Properties>
    <Item class="Part" referent="RBX1">
      <Properties>
        <string name="Name">Handle</string>
        <bool name="Anchored">false</bool>
        <bool name="CanCollide">false</bool>
        <bool name="CanQuery">true</bool>
        <bool name="CanTouch">true</bool>
        <bool name="Locked">false</bool>
        <bool name="Massless">false</bool>
        <Vector3 name="size"><X>{hx}</X><Y>{hy}</Y><Z>{hz}</Z></Vector3>
        <float name="Transparency">0</float>
      </Properties>
      <Item class="SpecialMesh" referent="RBX2">
        <Properties>
          <string name="Name">Mesh</string>
          <token name="MeshType">5</token>
          <Content name="MeshId"><url>rbxassetid://{mesh_id}</url></Content>
          <Content name="TextureId"><url>rbxassetid://{texture_id}</url></Content>
          <Vector3 name="Scale"><X>{sx}</X><Y>{sy}</Y><Z>{sz}</Z></Vector3>
          <Vector3 name="Offset"><X>0</X><Y>0</Y><Z>0</Z></Vector3>
        </Properties>
      </Item>
      <Item class="Attachment" referent="RBX3">
        <Properties>
          <string name="Name">{att}</string>
{cframe("CFrame", p)}
          <bool name="Visible">false</bool>
        </Properties>
      </Item>
      <Item class="StringValue" referent="RBX4">
        <Properties>
          <string name="Name">AvatarPartScaleType</string>
          <string name="Value">Classic</string>
        </Properties>
      </Item>
    </Item>
  </Item>
</roblox>
"""
    open(out, 'w').write(xml)
    print(f"  {out}   mesh={mesh_id}  textura={texture_id}")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
