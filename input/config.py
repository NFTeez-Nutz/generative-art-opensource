#!/usr/bin/env python3

from os import listdir, path
from os.path import isfile, join

# /**************************************************************
# * UTILITY FUNCTIONS
# * - scroll to BEGIN CONFIG to provide the config values
# *************************************************************/
dir = path.dirname(path.realpath(__file__))

# adds a rarity to the configuration. This is expected to correspond with a directory containing the rarity for each defined layer
# @param _id - id of the rarity
# @param _from - number in the edition to start this rarity from
# @param _to - number in the edition to generate this rarity to
# @return a rarity object used to dynamically generate the NFTs
def addRarity(_id, _from, _to):
    _rarityWeight = {
        "value": _id,
        "from": _from,
        "to": _to,
        "layerPercent": {}
    }
    return _rarityWeight

# get the name without last 4 characters -> slice .png from the name
def cleanName(_str):
    return _str[:-4]

# reads the filenames of a given folder and returns it with its name and path
def getElements(_path, _elementCount=None):
    filenames = [f for f in listdir(_path) if isfile(join(_path, f)) and ".png" in f]
    elements = []
    for f in filenames:
        elements.append({
            'id': _elementCount,
            'name': cleanName(f),
            'path': f"{_path}/{f}"
        })
    return elements

# adds a layer to the configuration. The layer will hold information on all the defined parts and 
# where they should be rendered in the image
# @param _id - id of the layer
# @param _position - on which x/y value to render this part
# @param _size - of the image
# @return a layer object used to dynamically generate the NFTs
def addLayer(_id, _position=None, _size=None):
    if not _position:
        _position = { 'x': 0, 'y': 0}
    if not _size:
        _size = { 'width': width, 'height': height }
    # add two different dimension for elements:
    # - all elements with their path information
    # - only the ids mapped to their rarity
    elements = {}
    elementCount = 0
    elementIdsForRarity = {}
    for rarityWeight in rarityWeights:
        elementsForRarity = getElements(f"{dir}/{_id}/{rarityWeight['value']}")

        elementIdsForRarity[rarityWeight['value']] = []
        for _elementForRarity in elementsForRarity:
            _elementForRarity["id"] = f"{editionDnaPrefix}{elementCount}"
            # elements['arr'].append(_elementForRarity)
            elementIdsForRarity[rarityWeight['value']].append(_elementForRarity['id'])
            elementCount += 1
        elements[rarityWeight['value']] = elementsForRarity

    elementsForLayer = {
        "id": _id,
        "position": _position,
        "size": _size,
        "elements": elements,
        "elementIdsForRarity": elementIdsForRarity
    }
    return elementsForLayer

# adds layer-specific percentages to use one vs another rarity
# @param _rarityId - the id of the rarity to specifiy
# @param _layerId - the id of the layer to specifiy
# @param _percentages - an object defining the rarities and the percentage with which a given rarity for this layer should be used
def addRarityPercentForLayer(_rarityId, _layerId, _percentages):
    _rarityFound = False
    for _rarityWeight in rarityWeights:
        if (_rarityWeight['value'] == _rarityId):
            _percentArray = []
            for percentType in _percentages:
                _percentArray.append({
                    "id": percentType,
                    "percent": _percentages[percentType]
                })
                _rarityWeight['layerPercent'][_layerId] = _percentArray
                _rarityFound = True
    if not _rarityFound:
        print(f"rarity ${_rarityId} not found, failed to add percentage information")

# /**************************************************************
#  * BEGIN CONFIG
#  *************************************************************/

# image width in pixels
width = 1000
# image height in pixels
height = 1000
# description for NFT in metadata file
description = "This is an NFT made by the coolest generative code."
# base url to use in metadata file
# the id of the nft will be added to this url, in the example e.g. https://hashlips/nft/1 for NFT with id 1
baseImageUri = "https://hashlips/nft"
# id for edition to start from
startEditionFrom = 1
# amount of NFTs to generate in edition
editionSize = 10
# prefix to add to edition dna ids (to distinguish dna counts from different generation processes for the same collection)
editionDnaPrefix = 0

# create required weights
# for each weight, call 'addRarity' with the id and from which to which element this rarity should be applied
rarityWeights = [
  addRarity('super_rare', 1, 1),
  addRarity('rare', 2, 5),
  addRarity('original', 5, 10)
]

# create required layers
# for each layer, call 'addLayer' with the id and optionally the positioning and size
# the id would be the name of the folder in your input directory, e.g. 'ball' for ./input/ball
layers = [
  addLayer('ball', { 'x': 0, 'y': 0 }, { 'width': width, 'height': height }),
  addLayer('eye color'),
  addLayer('iris'),
  addLayer('shine'),
  addLayer('bottom lid'),
  addLayer('top lid')
]

# provide any specific percentages that are required for a given layer and rarity level
# all provided options are used based on their percentage values to decide which layer to select from
addRarityPercentForLayer('super_rare', 'ball', { 'super_rare': 33, 'rare': 33, 'original': 33 })
addRarityPercentForLayer('super_rare', 'eye color', { 'super_rare': 50, 'rare': 25, 'original': 25 })
addRarityPercentForLayer('original', 'eye color', { 'super_rare': 50, 'rare': 25, 'original': 25 })