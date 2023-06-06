#Noesis Python model import+export test module, imports/exports some data from/to a made-up format

from inc_noesis import *
import struct

#registerNoesisTypes is called by Noesis to allow the script to register formats.
#Do not implement this function in script files unless you want them to be dedicated format modules!
def registerNoesisTypes():
    handle = noesis.register("God Hand .dat Container", ".dat")
    noesis.setHandlerTypeCheck(handle, noepyCheckType)
    noesis.setHandlerLoadModel(handle, noepyLoadModel)
    return 1

#check if it's this type based on the data
def noepyCheckType(data):
    global ModelPointers
    global TexturePointers
    ModelPointers = []
    TexturePointers = []

    if len(data) < 16:
        return 0

    bs = NoeBitStream(data, NOE_LITTLEENDIAN)
    ChunkCount = bs.readInt()
    if ChunkCount <= 0:
        return 0
    
    #read the first pointer

    '''ChunkPointer = bs.readUInt()
    
    if ChunkPointer <= 0:
        return 0'''
    
    ChunkPointers = [bs.readUInt() for i in range(ChunkCount)]

    for i in range(ChunkCount):
        type = noeStrFromBytes(bs.readBytes(4))
        if type == "MD":
            ModelPointers.append(ChunkPointers[i])
        elif type == "TM3":
            TexturePointers.append(ChunkPointers[i])

    if len(ModelPointers) > 0 or len(TexturePointers) > 0:
        return 1
    else:
        return 0
    

#read it
def noepyLoadModel(data, mdlList):
    texList = []
    texList = LoadTextures(data, texList)
    mats = []

    #create a material for each texture
    for tex in texList:
        texName = tex.name
        matName = texName + ".mat"
        mat = NoeMaterial(matName, texName)
        mat.setTexture(texName)
        mats.append(mat)

    bs = NoeBitStream(data)
    ctx = rapi.rpgCreateContext()

    numMeshes = len(ModelPointers)
    for i in range(0, numMeshes):
        bs.seek(ModelPointers[i])
        #check the chunk type
        type = noeStrFromBytes(bs.readBytes(4))
        if type == "scr":
            #print("found scr Chunk")
            scrPos = bs.getOffset() - 4
            #print("scrPos = %d" % scrPos)
            bs.seek(4, NOESEEK_REL)
            MeshCount = bs.readUInt()
            bs.seek(4, NOESEEK_REL)
            if MeshCount <= 0:
                return 0
            MeshPointers = [bs.readUInt() for i in range(MeshCount)]
            #print("Mesh Count = %d" % MeshCount)
            #print(MeshPointers)
            #align
            #print("Offset = %d" % bs.getOffset())
            padding = 16 - ((bs.getOffset() - scrPos) % 16)
            #print("Padding = %d" % padding)
            bs.seek(padding, NOESEEK_REL)
            for j in range(MeshCount):
                bs.seek(scrPos + MeshPointers[j], NOESEEK_ABS)
                MeshDataPointer = bs.readInt()
                #print("Mesh Data Pointer = %d" % MeshDataPointer)
                unk1 = bs.readShort()
                unk2 = bs.readShort()
                MeshName = noeStrFromBytes(bs.readBytes(8))
                #print("Mesh Name = %s" % MeshName)
                rapi.rpgSetName(MeshName)

                bs.seek(scrPos + MeshPointers[j] + MeshDataPointer, NOESEEK_ABS)
                meshPos = bs.getOffset()
                MeshMagic = noeStrFromBytes(bs.readBytes(4))
                #print("Mesh Magic = %s" % MeshMagic)
                HeaderSize = bs.readUInt()
                #print("Header Size = %d" % HeaderSize)
                unkCount = bs.readUShort()
                #print("unkCount = %d" % unkCount)
                VertexBufferCount = bs.readUShort()
                #print("Vertex Buffer Count = %d" % VertexBufferCount)
                bs.seek(20, NOESEEK_REL)
                VertexBufferPointers = [bs.readUInt() for i in range(VertexBufferCount)]
                if VertexBufferCount > 4:
                    bs.seek(4*(8 - VertexBufferCount), NOESEEK_REL)
                bs.seek(16*unkCount, NOESEEK_REL)
                for vb in range(VertexBufferCount):
                    VBPos = meshPos + VertexBufferPointers[vb]
                    bs.seek(VBPos, NOESEEK_ABS)
                    VertexPosPointer = bs.readUInt()
                    #print("Vertex Pos Pointer = %d" % VertexPosPointer)
                    VertexNormalsPointer = bs.readUInt()
                    #print("UV Pointer = %d" % VertexNormalsPointer)
                    VertexUVPointer = bs.readUInt()
                    #print("UV Pointer = %d" % VertexUVPointer)
                    VertexColorsPointer = bs.readUInt()
                    #print("Vertex Colors Pointer = %d" % VertexColorsPointer)
                    VertexWeightsPointer = bs.readUInt()
                    #print("Vertex Weights Pointer = %d" % VertexWeightsPointer)
                    VertexCount = bs.readUShort()
                    #print("Vertex Count = %d" % VertexCount)
            
                    bs.seek(2, NOESEEK_REL)
                    
                    bs.seek(VBPos + VertexPosPointer, NOESEEK_ABS)
                    positions = b''
                    triangles = b''
                    indicesCount = 0

                    #add triangles and vertices as we go
                    for v in range(VertexCount):
                        positions += bs.readBytes(12)
                        triFlag = bs.readUInt()
                        if triFlag == 32768:
                            continue
                        elif triFlag == 0:
                            triangles += struct.pack('iii', v-2, v-1, v)
                            indicesCount += 3
                        elif triFlag == 1:
                            triangles += struct.pack('iii', v-1, v-2, v)
                            indicesCount += 3

                    #seek to normals
                    bs.seek(VBPos + VertexNormalsPointer, NOESEEK_ABS)
                    normals = b''
                    #3 bytes packed
                    for v in range(VertexCount):
                        normals += bs.readBytes(3)
                        bs.seek(1, NOESEEK_REL)

                    #seek to UVs
                    bs.seek(VBPos + VertexUVPointer, NOESEEK_ABS)
                    uvs = b''
                    for i in range(VertexCount):
                        u = bs.readShort() / 4096
                        v = bs.readShort() / 4096
                        uvs += struct.pack('ff', u, v)
                    
                    #seek to colors
                    bs.seek(VBPos + VertexColorsPointer, NOESEEK_ABS)
                    colors = bs.readBytes(VertexCount*4)

                    #seek to weights
                    bs.seek(VBPos + VertexWeightsPointer, NOESEEK_ABS)
                    weightIndices = b''
                    weights = b''
                    #4 byte indices + 4 byte weights, all weights add up to 100
                    for v in range(VertexCount):
                        weightIndices += bs.readBytes(4)

                        weightValue = bs.readByte()
                        weights += struct.pack('f', weightValue/100)

                        weightValue = bs.readByte()
                        weights += struct.pack('f', weightValue/100)

                        weightValue = bs.readByte()
                        weights += struct.pack('f', weightValue/100)

                        weightValue = bs.readByte()
                        weights += struct.pack('f', weightValue/100)
                    
                    #add the positions and triangles to the rapi
                    rapi.rpgBindPositionBuffer(positions, noesis.RPGEODATA_FLOAT, 12)
                    rapi.rpgBindNormalBuffer(normals, noesis.RPGEODATA_BYTE, 3)
                    rapi.rpgBindUV1Buffer(uvs, noesis.RPGEODATA_FLOAT, 8)
                    #rapi.rpgBindColorBuffer(colors, noesis.RPGEODATA_UBYTE, 4, 4)
                    rapi.rpgBindBoneIndexBuffer(weightIndices, noesis.RPGEODATA_UBYTE, 4, 1)
                    rapi.rpgBindBoneWeightBuffer(weights, noesis.RPGEODATA_FLOAT, 4, 1)
                    rapi.rpgCommitTriangles(triangles, noesis.RPGEODATA_INT, indicesCount, noesis.RPGEO_TRIANGLE, 1)
                    rapi.rpgClearBufferBinds()

                mdl = rapi.rpgConstructModel()
                mdl.setModelMaterials(NoeModelMaterials(texList, mats))   
            mdlList.append(mdl)
             

    return 1

class TIM3:
    def __init__(self):
        self.Magic = 'TIM3'
        self.Version = 0
        self.Format = 0
        self.TextureCount = 0
        self.TotalSize = 0
        self.ClutSize = 0
        self.TextureSize = 0
        self.HeaderSize = 0
        self.ClutColorCount = 0
        self.TextureFormat = 0
        self.MipmapCount = 0
        self.ClutType = 0
        self.PixelFormat = 0
        self.Width = 0
        self.Height = 0
        self.GsTexRegister = 0
        self.GsTexRegister = 0
        self.GsFlagsRegister = 0
        self.GsClutRegister = 0
        self.MipMapsHeader = MipMapsHeader()
        self.TextureData = bytearray()
        self.Colors = []

class MipMapsHeader:
    def __init__(self):
        self.MiptbpRegister = 0
        self.MipMapSizes = [0] * 8

def GetColorType(value):
    switcher = {
        0: "Undefined",
        1: "A1B5G5R5",
        2: "X8B8G8R8",
        3: "A8B8G8R8",
        4: "4-bit Indexed",
        5: "8-bit Indexed"
    }
    return switcher.get(value, "UNKNOWN")

def tim3Read(data, offset):
    bs = NoeBitStream(data, NOE_LITTLEENDIAN)
    bs.seek(offset, NOESEEK_ABS)

    tim3 = TIM3()
    bs.readBytes(4)
    tim3.Version = bs.readUByte()
    tim3.Format = bs.readUByte()
    tim3.TextureCount = bs.readUShort()

    bs.seek(8, NOESEEK_REL) #padding

    tim3.TotalSize = bs.readUInt()
    tim3.ClutSize = bs.readUInt()
    tim3.TextureSize = bs.readUInt()
    tim3.HeaderSize = bs.readUShort()
    tim3.ClutColorCount = bs.readUShort()
    tim3.TextureFormat = bs.readUByte()
    tim3.MipmapCount = bs.readUByte()
    tim3.ClutType = bs.readUByte()
    tim3.PixelFormat = bs.readUByte()
    tim3.Width = bs.readUShort()
    tim3.Height = bs.readUShort()
    
    bs.seek(24, NOESEEK_REL) #gs registers

    if tim3.MipmapCount > 1:
        tim3.MipMapsHeader.MiptbpRegister = bs.readInt()
        tim3.MipMapsHeader.MiptbpRegister = bs.readInt()
        tim3.MipMapsHeader.MiptbpRegister = bs.readInt()
        tim3.MipMapsHeader.MiptbpRegister = bs.readInt()
        for i in range(8):
            tim3.MipMapsHeader.MipMapSizes[i] = bs.readInt()

    tim3.TextureData = bs.readBytes(tim3.TextureSize)
    tim3.Colors = bs.readBytes(tim3.ClutSize)

    return tim3

def GetColorType(value):
    switcher = {
        0: "Undefined",
        1: "r5 g5 b5 a1",
        2: "r8 g8 b8 x8",
        3: "r8 g8 b8 a8",
        4: 4,
        5: 8
    }
    return switcher.get(value, "UNKNOWN")

def tm3Read(data, offset):
    bs = NoeBitStream(data, NOE_LITTLEENDIAN)
    bs.seek(0, NOESEEK_ABS)

    texList = []

    bs.seek(offset, NOESEEK_ABS)
    
    bs.seek(4, NOESEEK_REL) #magic
    TexturesCount = bs.readUInt()

    bs.seek(8, NOESEEK_REL) #unk bytes

    TexOffsets = [bs.readUInt() for i in range(TexturesCount)]

    if (TexturesCount * 4) % 8 != 0:
        bs.seek((8 - ((TexturesCount * 4) % 8)), NOESEEK_REL)

    TexNames = [noeStrFromBytes(bs.readBytes(8)) for i in range(TexturesCount)]

    for i in range(TexturesCount):
        
        tim3 = tim3Read(data, offset + TexOffsets[i])

        PixelFormat = GetColorType(tim3.PixelFormat)
        ClutType = GetColorType(tim3.ClutType)

        if tim3.Width >= 128 and tim3.Height >= 128:
            if PixelFormat == 4:
                TexData = rapi.imageUntwiddlePS2(tim3.TextureData, tim3.Width, tim3.Height, 4)
                TexData = rapi.imageDecodeRawPal(TexData, tim3.Colors, tim3.Width, tim3.Height, 4, ClutType)
                TexData = rapi.imageScaleRGBA32(TexData, (1.0, 1.0, 1.0, 2.0), tim3.Width, tim3.Height)
            elif PixelFormat == 8:
                TexData = rapi.imageUntwiddlePS2(tim3.TextureData, tim3.Width, tim3.Height, 8)
                TexData = rapi.imageDecodeRawPal(TexData, tim3.Colors, tim3.Width, tim3.Height, 8, ClutType, 1)
                TexData = rapi.imageScaleRGBA32(TexData, (1.0, 1.0, 1.0, 2.0), tim3.Width, tim3.Height)
        
        else:
            if PixelFormat == 4:
                TexData = rapi.imageDecodeRawPal(tim3.TextureData, tim3.Colors, tim3.Width, tim3.Height, 4, ClutType)
                TexData = rapi.imageScaleRGBA32(TexData, (1.0, 1.0, 1.0, 2.0), tim3.Width, tim3.Height)

            elif PixelFormat == 8:
                TexData = rapi.imageDecodeRawPal(tim3.TextureData, tim3.Colors, tim3.Width, tim3.Height, 8, ClutType, 1)
                TexData = rapi.imageScaleRGBA32(TexData, (1.0, 1.0, 1.0, 2.0), tim3.Width, tim3.Height)
        
        texList.append(NoeTexture(TexNames[i], tim3.Width, tim3.Height, TexData, noesis.NOESISTEX_RGBA32))

    return texList

def LoadTextures(data, texList):
    print("Loading textures...")
    bs = NoeBitStream(data, NOE_LITTLEENDIAN)
    for pointer in TexturePointers:
        tm3 = tm3Read(data, pointer)
        for tex in tm3:
            texList.append(tex)
    
    print("Loaded %d textures" % len(texList))
    
    return texList
