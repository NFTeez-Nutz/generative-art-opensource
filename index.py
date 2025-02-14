#!/usr/bin/env python3

import math
import random
import colorsys
import json
from PIL import Image, ImageDraw, ImageFont
from input.config import (
    layers,
    width,
    height,
    description,
    baseImageUri,
    editionSize,
    startEditionFrom,
    rarityWeights,
    obstructions
)

# saves the generated image to the output folder, using the edition count as the name
def saveImage(_editionCount, _img):
    _img.save(f"./output/{_editionCount}.png")

# adds a signature to the top left corner of the canvas
def signImage(_sig, _img):
    draw = ImageDraw.Draw(_img)
    font = ImageFont.truetype("fonts/COUR.TTF", 30)
    draw.text(
        (40, 40),
        f"{_sig}",
        (255,255,255),
        anchor="lt",
        font=font)

# generate a random color hue
def genColor():
    hue = math.floor(random.random() * 360)
    pastel = tuple(int(color*100) for color in colorsys.hls_to_rgb(hue, 0.85, 1))
    return pastel


def drawBackground(_img):
    draw = ImageDraw.Draw(_img)
    fill = genColor()
    draw.rectangle([(0,0),_img.size], fill=fill)

# add metadata for individual nft edition
def generateMetadata(_dna, _edition, _attributesList):
    tempMetadata = {
        'dna': "".join(_dna),
        'name': f"#{_edition}",
        'description': description,
        'image': f"{baseImageUri}/{_edition}",
        'edition': f"{_edition}",
        'attributes': _attributesList
    }
    return tempMetadata

# prepare attributes for the given element to be used as metadata
def getAttributeForElement(_element):
    selectedElement = _element['layer']['selectedElement']
    attribute = {
        'trait_type': selectedElement['property'],
        'value': selectedElement['name']
    }
    return attribute

# loads an image from the layer path
# returns the image in a format usable by canvas
def loadLayerImg(_layer):
    image = Image.open(f"{_layer['selectedElement']['path']}")
    return {
        'layer': _layer,
        'loadedImage': image
    }

def drawElement(_element, _img):
    elementImg = _element['loadedImage']
    layerwidth = _element['layer']['size']['width']
    layerheight = _element['layer']['size']['height']
    ewidth, eheight = _element['loadedImage'].size
    if ewidth != layerwidth or eheight != layerheight:
        elementImg = elementImg.resize((layerwidth,layerheight))

    print()
    _img.paste(
        elementImg,
        (_element['layer']['position']['x'],
        _element['layer']['position']['y']),
        elementImg)


# check the configured layer to find information required for rendering the layer
# this maps the layer information to the generated dna and prepares it for
# drawing on a canvas
def constructLayerToDna(_dna, _layers, _rarity):
    def f(layer, index):
        rarities = [layer['elements'][rarity] for rarity in layer['elements']]
        elementRarities = [element for elements in rarities for element in elements]
        selectedElement = next(element for element in elementRarities if element['id'] == _dna[index])
        return {
            'position': layer['position'],
            'size': layer['size'],
            'selectedElement': {**selectedElement, 'rarity': _rarity }
        }
    mappedDnaToLayers = map(f,_layers, range(len(_layers)))
    return mappedDnaToLayers

# check if the given dna is contained within the given dnaList 
# return true if it is, indicating that this dna is already in use and should be recalculated
def isDnaUnique(_DnaList, _dna):
    foundDna = next((False for i in _DnaList if ''.join(i) == ''.join(_dna)), True)
    return foundDna

def getRandomRarity(_rarityOptions):
    randomPercent = random.random() * 100
    percentCount = 0

    for i in range(len(_rarityOptions)):
        percentCount += _rarityOptions[i]['percent']
        if percentCount >= randomPercent:
            return _rarityOptions[i]['id']
    return _rarityOptions[0]['id']

# create a dna based on the available layers for the given rarity
# use a random part for each layer
def createDna(_layers, _rarity):
    randNum = []
    selectedElements = []
    _rarityWeight = next(rw for rw in rarityWeights if rw['value'] == _rarity)
    for layer in _layers:
        obsd = True
        while obsd:
            obsd = False
            id = 0
            num = math.floor(random.random() * len(layer['elementIdsForRarity'][_rarity]))
            if _rarityWeight and layer['id'] in _rarityWeight['layerPercent']:
                _rarityForLayer = getRandomRarity(_rarityWeight['layerPercent'][layer['id']])
                num = math.floor(random.random() * len(layer['elementIdsForRarity'][_rarityForLayer]))
                id = layer['elementIdsForRarity'][_rarityForLayer][num]
            else:
                id = layer['elementIdsForRarity'][_rarity][num]
            
            # Check for obstructions
            rarities = [layer['elements'][rarity] for rarity in layer['elements']]
            elementRarities = [element for elements in rarities for element in elements]
            nextElement = next(element for element in elementRarities if element['id'] == id)['name']
            for obs in obstructions:
                if(nextElement in obs and all(x in selectedElements+[nextElement] for x in obs)):
                    print(f"obs with {obs} found")
                    obsd = True
                    break
        selectedElements.append(nextElement)
        randNum.append(id)

    return randNum

# holds which rarity should be used for which image in edition
rarityForEdition = []

# get the rarity for the image by edition number that should be generated
def getRarity(_editionCount):
    if not len(rarityForEdition):
        rarityWeights.sort(key= lambda r: r['from'], reverse=True) # Honor rarityWeights
        for rarityWeight in rarityWeights:
            for i in range(rarityWeight['from'], rarityWeight['to'] + 1):
                rarityForEdition.append(rarityWeight['value'])
    return rarityForEdition[editionSize  - _editionCount]

def writeMetaData(_data):
    with open("./output/_metadata.json", 'a') as f:
        f.write(_data)

# holds which dna has already been used during generation
dnaListByRarity = {}

# holds metadata for all NFTs
metadataList = []
dnaList = []

from multiprocessing import Pool, Lock, Manager
import os

lock = None

# Multithreaded implementation
def startCreatingMulti(_max_processes=None):
    if not _max_processes:
        _max_processes = os.cpu_count()
    max_processes = _max_processes

    global lock
    lock = Lock()

    print('##################')
    print('# Generative Art')
    print('# - Create your NFT collection')
    print('###########')

    print()
    print('start creating NFTs.')

    # clear meta data from previous run
    writeMetaData("")

    # prepare dnaList object
    for rarityWeight in rarityWeights:
        dnaListByRarity[rarityWeight['value']] = []


    metadataList = []
    # Generate art, regenerate any duplicates found
    duplicates = True
    ids = range(startEditionFrom,startEditionFrom+editionSize)
    while duplicates:
        duplicates = False
        # Start processes
        with Pool(max_processes) as pool:
            results = pool.map(creator, ids)

        newMetadataList, newDnaList = zip(*results)
        metadataList = metadataList + list(newMetadataList)

        # Check for duplicates
        nonunique_ids = []
        for dna in list(newDnaList):
            id = dna['id']
            rarity = dna['rarity']
            newDna = dna['dna']
            if not isDnaUnique(dnaListByRarity[rarity], newDna):
                nonunique_ids.append(id)
                duplicates = True
            else:
                dnaListByRarity[rarity].append(newDna)
        ids = nonunique_ids

    writeMetaData(json.dumps(metadataList))

# Worker thread function
def creator(_id):
    editionCount = _id
    print('-----------------')
    print(f'creating NFT {editionCount} of {editionSize}')

    # get rarity from to config to create NFT as
    rarity = getRarity(editionCount)
    # print(f'- rarity: {rarity}')

    # calculate the NFT dna by getting a random part for each layer/feature 
    # based on the ones available for the given rarity to use during generation
    newDna = createDna(layers, rarity)
    while not isDnaUnique(dnaListByRarity[rarity], newDna):
        # recalculate dna as this has been used before.
        print(f"found duplicate DNA {'-'.join(newDna)} recalculate...")
        newDna = createDna(layers, rarity)
    
    # print(f"- dna: {'-'.join(newDna)}")

    # propagate information about required layer contained within config into a mapping object
    # = prepare for drawing
    results = constructLayerToDna(newDna, layers, rarity)
    loadedElements = []

    # load all images to be used by canvas
    for layer in results:
        loadedElements.append(loadLayerImg(layer))

    # elements are loaded asynchronously
    # -> await for all to be available before drawing the image
    elementArray = loadedElements
    img = Image.new('RGB', (height, width), (255, 255, 255))
    drawBackground(img)
    attributesList = []
    for element in elementArray:
        drawElement(element, img)
        attributesList.append(getAttributeForElement(element))
    # add an image signature as the edition count to the top left of the image
    # signImage(f'#{editionCount}', img)
    nftMetadata = generateMetadata(newDna, editionCount, attributesList)
    # write the image to the output directory
    with lock:
        saveImage(editionCount, img)
    print('- metadata: ' + json.dumps(nftMetadata) + '\n- edition ' + str(editionCount) + ' created.\n')
    dnaListByRarity[rarity].append(newDna)
    tokenData = {
        'id' : _id,
        'rarity' : rarity,
        'dna' : newDna
    }
    return (nftMetadata,tokenData)

# Create generative art by using the canvas api
def startCreating():
    print('##################')
    print('# Generative Art')
    print('# - Create your NFT collection')
    print('###########')

    print()
    print('start creating NFTs.')

    # clear meta data from previous run
    writeMetaData("")

    # prepare dnaList object
    for rarityWeight in rarityWeights:
        dnaListByRarity[rarityWeight['value']] = []

    # create NFTs from startEditionFrom to editionSize
    editionCount = startEditionFrom
    while editionCount <= editionSize:
        print('-----------------')
        print(f'creating NFT {editionCount} of {editionSize}')

        # get rarity from to config to create NFT as
        rarity = getRarity(editionCount)
        print(f'- rarity: {rarity}')

        # calculate the NFT dna by getting a random part for each layer/feature 
        # based on the ones available for the given rarity to use during generation
        newDna = createDna(layers, rarity)
        while not isDnaUnique(dnaListByRarity[rarity], newDna):
            # recalculate dna as this has been used before.
            print(f"found duplicate DNA {'-'.join(newDna)} recalculate...")
            newDna = createDna(layers, rarity)
        
        print(f"- dna: {'-'.join(newDna)}")

        # propagate information about required layer contained within config into a mapping object
        # = prepare for drawing
        results = constructLayerToDna(newDna, layers, rarity)
        loadedElements = []

        # load all images to be used by canvas
        for layer in results:
            loadedElements.append(loadLayerImg(layer))

        # elements are loaded asynchronously
        # -> await for all to be available before drawing the image
        elementArray = loadedElements
        img = Image.new('RGB', (height, width), (255, 255, 255))
        drawBackground(img)
        attributesList = []
        for element in elementArray:
            drawElement(element, img)
            attributesList.append(getAttributeForElement(element))
        # add an image signature as the edition count to the top left of the image
        # signImage(f'#{editionCount}', img)
        # write the image to the output directory
        saveImage(editionCount, img)
        nftMetadata = generateMetadata(newDna, editionCount, attributesList)
        metadataList.append(nftMetadata)
        print('- metadata: ' + json.dumps(nftMetadata))
        print('- edition ' + str(editionCount) + ' created.')
        print()
        dnaListByRarity[rarity].append(newDna)
        editionCount += 1
    writeMetaData(json.dumps(metadataList))

# Initiate code
# startCreating()
startCreatingMulti()