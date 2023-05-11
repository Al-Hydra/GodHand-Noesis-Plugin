#Noesis Python model import+export test module, imports/exports some data from/to a made-up format

from inc_noesis import *
import struct

#registerNoesisTypes is called by Noesis to allow the script to register formats.
#Do not implement this function in script files unless you want them to be dedicated format modules!
def registerNoesisTypes():
	handle = noesis.register("God Hand .dat Container", ".dat")
	noesis.setHandlerTypeCheck(handle, noepyCheckType)
	noesis.setHandlerLoadModel(handle, noepyLoadModel)
	#noesis.setHandlerWriteModel(handle, noepyWriteModel)
	#noesis.setHandlerWriteAnim(handle, noepyWriteAnim)
	#any noesis.NMSHAREDFL_* flags can be applied here, to affect the model which is handed off to the exporter.
	#adding noesis.NMSHAREDFL_FLATWEIGHTS_FORCE4 would force us to 4 weights per vert.
	#noesis.setTypeSharedModelFlags(handle, noesis.NMSHAREDFL_FLATWEIGHTS)

	noesis.logPopup()
	##print("The log can be useful for catching debug #prints from preview loads.\nBut don't leave it on when you release your script, or it will probably annoy people.")
	return 1

#check if it's this type based on the data
def noepyCheckType(data):
    if len(data) < 16:
        return 0

    bs = NoeBitStream(data, NOE_LITTLEENDIAN)
    #we'll try to read until we reach the first chunk
    ChunkCount = bs.readInt()
    if ChunkCount <= 0:
        return 0
    
    #read the first pointer
    ChunkPointer = bs.readUInt()
    if ChunkPointer <= 0:
        return 0
    
    #seek to the first chunk
    bs.seek(ChunkPointer, NOESEEK_ABS)
    #read the first 4 bytes as a string
    ChunkType = noeStrFromBytes(bs.readBytes(4))
    if ChunkType in ("scr", "TM3", "mdb", "mtb3", "SEQ"):
        #print("found %s Chunk" % (ChunkType))
        return 1
    else:
        return 0

#read it
def noepyLoadModel(data, mdlList):
    bs = NoeBitStream(data)
	#we start from 0x0
    ChunkCount = bs.readUInt()
    if ChunkCount <= 0:
        return 0
    
    #read the first pointer
    ChunkPointers = [bs.readUInt() for i in range(ChunkCount)]
    #print("Chunk Count = %d" % ChunkCount)
    #print(ChunkPointers)
    ModelPointers = []
    for i in range(ChunkCount):
        type = noeStrFromBytes(bs.readBytes(4))
        if type == "MD":
            ModelPointers.append(ChunkPointers[i])
	
    #print("There are %d models in this container" % len(ModelPointers))

	#no need to explicitly free the context (created contexts are auto-freed after the handler), but DO NOT hold any references to it outside of this method
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
            mdlList.append(mdl)
            

    return 1