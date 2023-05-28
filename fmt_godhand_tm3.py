from inc_noesis import *

def registerNoesisTypes():
    handle = noesis.register("GOD HAND Texture Container", ".tim3")
    noesis.setHandlerTypeCheck(handle, noepyCheckType)
    noesis.setHandlerLoadRGBA(handle, noepyLoadRGBA)

    return 1

def noepyCheckType(data):
    bs = NoeBitStream(data, NOE_LITTLEENDIAN)

    if noeStrFromBytes(bs.readBytes(4)) != "TM3":
        return 0
    else:
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

def tm3Read(data):
    texList = []
    bs = NoeBitStream(data, NOE_LITTLEENDIAN)
    bs.seek(0, NOESEEK_ABS)

    
    bs.seek(4, NOESEEK_REL) #magic
    TexturesCount = bs.readUInt()

    bs.seek(8, NOESEEK_REL) #unk bytes

    TexOffsets = [bs.readUInt() for i in range(TexturesCount)]

    if (TexturesCount * 4) % 8 != 0:
        bs.seek((8 - ((TexturesCount * 4) % 8)), NOESEEK_REL)

    TexNames = [noeStrFromBytes(bs.readBytes(8)) for i in range(TexturesCount)]

    for i in range(TexturesCount):
        
        tim3 = tim3Read(data, TexOffsets[i])

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

def noepyLoadRGBA(data, texList):
    tm3 = tm3Read(data)
    for tex in tm3:
        texList.append(tex)
    
    return 1
