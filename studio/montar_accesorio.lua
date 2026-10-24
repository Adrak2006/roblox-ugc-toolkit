-- Pegar en la BARRA DE COMANDOS de Roblox Studio (Ver -> Barra de comandos).
-- Monta un Accessory con el Attachment EXACTO del original, sin colocar nada a mano.
-- Cambia los ids por los de TU malla y TU textura después de subirlas, y la CFrame por la
-- del accesorio de referencia (la saca rbxm.py / accesorio.py del .rbxm original).

local MESH_ID    = 0        -- <-- tu MeshId
local TEXTURE_ID = 0        -- <-- tu TextureId
local TIPO       = Enum.AccessoryType.Back
local ATTACH     = "BodyBackAttachment"       -- HatAttachment para sombreros, etc.
local CFRAME     = CFrame.new(0, 0.21148, -1.0476)   -- ejemplo: unas alas de espalda

local acc  = Instance.new("Accessory")
acc.Name   = "MiAccesorio"
acc.AccessoryType = TIPO

local h    = Instance.new("Part")
h.Name, h.Size, h.CanCollide, h.Anchored = "Handle", Vector3.new(1,1,1), false, false
h.Parent   = acc

local mesh = Instance.new("SpecialMesh")
mesh.MeshType  = Enum.MeshType.FileMesh
mesh.MeshId    = "rbxassetid://" .. MESH_ID
mesh.TextureId = "rbxassetid://" .. TEXTURE_ID
mesh.Scale     = Vector3.new(1,1,1)
mesh.Parent    = h

local att  = Instance.new("Attachment")
att.Name   = ATTACH
att.CFrame = CFRAME
att.Parent = h

local sc   = Instance.new("StringValue")
sc.Name, sc.Value, sc.Parent = "AvatarPartScaleType", "Classic", h

acc.Parent = workspace
print("Accesorio montado en workspace:", acc:GetFullName())
