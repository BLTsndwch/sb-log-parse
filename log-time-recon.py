#! /usr/bin/python
#%% imports

import json
import os
import re
import struct
import pandas
import datetime
import statistics
import matplotlib.pyplot as plt
import argparse
from si_prefix import si_format
import sys

#%% args
parser = argparse.ArgumentParser(description="Parse a SensorBoard can log")
parser.add_argument('inputFile', nargs='*', default=None, help="the can log to parse")
args = parser.parse_args()


#%% files
dirname = os.path.dirname(__file__)
configFolder = os.path.join(dirname, 'configs')
# configFolder = r"configs"
configpaths = []

for file in os.listdir(configFolder):
    if file.endswith(r".json"):
        configpaths.append(os.path.join(configFolder, file))

print("Found configs: ", configpaths)

# print(json.dumps(canformat, indent=4, sort_keys=True))
# for x in canformat:
    # print("{}\n".format(x["can_id"]))

#%% parse configs
class CanFrameInfo(object):
    def __init__(self,id,datatype,name,offset,checkBounds,minValue=None,maxValue=None,description=None):
        self.id = id
        self.description = description
        self.checkBounds = checkBounds
        self.dataTypeStr = datatype.rstrip()
        self.maxValue = maxValue
        self.minValue = minValue
        self.name = name
        self.offset = offset # Offset in bytes

        self.currentValue = None
        self.dataWidth = None
        self.parsestr = r''
        if (self.dataTypeStr == 'float32'):
            self.datatype = float
            self.dataWidth = 4
            self.parsestr = r'<' + r'x' * self.offset + r'f' + r'x' * (8 - self.offset - self.dataWidth)
        elif self.dataTypeStr == 'uint16':
            self.datatype = int
            self.dataWidth = 2
            self.parsestr = r'<' + r'x' * self.offset + r'H' + r'x' * (8 - self.offset - self.dataWidth)
        elif self.dataTypeStr == 'int16':
            self.datatype = int
            self.dataWidth = 2
            self.parsestr = r'<' + r'x' * self.offset + r'h' + r'x' * (8 - self.offset - self.dataWidth)
        elif self.dataTypeStr == 'uint8':
            self.datatype = int
            self.dataWidth = 1
            self.parsestr = r'<' + r'x' * self.offset + r'B' + r'x' * (8 - self.offset - self.dataWidth)
        elif self.dataTypeStr == 'uint32':
            self.datatype = int
            self.dataWidth = 4
            self.parsestr = r'<' + r'x' * self.offset + r'I' + r'x' * (8 - self.offset - self.dataWidth)
        elif self.dataTypeStr == 'bit':
            self.bitMask = 2**(7-(offset%8))
            self.offset = self.offset // 8
            self.datatype = bool
            self.dataWidth = 1
            self.parsestr = r'<' + r'x' * self.offset + r'B' + r'x' * (8 - self.offset - self.dataWidth)


    def parse(self, candata):
        candata = candata
        if len(candata) < 8:
            for _ in range(8-len(candata)):
                candata.append(0)
        if self.dataTypeStr == 'bit':
            self.currentValue = self.datatype(struct.unpack(self.parsestr, candata)[0] & self.bitMask)
            
        else:
            try:
                self.currentValue = self.datatype(struct.unpack(self.parsestr, candata)[0])
            except Exception as ex:
                print("Failed to parse:", ex)
                print(f"canid {self.id}, {self.datatype}")
                print("\t", len(candata), candata)
                print("\t", self.parsestr)

    def __repr__(self):
        info = f"""id={self.id} offset={self.offset} name={self.name}
        description={self.description}
        checkBounds={self.checkBounds} minValue={self.minValue} maxValue={self.maxValue}
        parseStr={self.parsestr}"""

        return info

database = {}

for configPath in configpaths:
    with open(configPath) as f:
        canformat = json.load(f)

    for config in canformat:
        # print(type(config))
        if config['can_id'] not in database:
            database[config['can_id']] = []

        database[config['can_id']].append(CanFrameInfo(
            id=config.get('can_id', None),
            datatype=config.get('datatype', None),
            name=config.get('name', None),
            offset=config.get('offset', None),
            checkBounds=config.get('check_bounds', None),
            minValue=config.get('min_value', None),
            maxValue=config.get('max_value', None),
            description=config.get('description', None)
        ))

dlcs = {}
headerlist = ['time']
headerstr = ""
for canid in sorted(database.items()):
    # print(canid, end='\n\n\n')
    highestByte = 0
    for datum in canid[1]:
        offset = datum.offset
        if (datum.dataWidth + offset) > highestByte:
            highestByte = datum.dataWidth + datum.offset

        headerlist.append(datum.name)
        headerstr = headerstr + datum.name + ", " 
    headerstr = headerstr[:-2] # remove trailing ,
    if highestByte > 8:

        print("Too big", canid)
    # print(canid[0], highestByte)
    # dlcs[canid[0]] = highestByte
    dlcs[canid[0]] = highestByte
    
# print(headerstr)
print("Config parse done.")

#%%
# args = {'inputFile': None}

fileLogPath = r"C:\Users\benlt\OneDrive\School\20211\Solar\incident\sd card\recon\221358"


#%%
ptrn = r"^\s*(?P<time>-?\d*.\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
mtch = re.compile(pattern=ptrn)

inputDataList = list()
regexFails = 0 
print("Opening ", fileLogPath)
with open(fileLogPath) as inputdata:
    for linenum, line in enumerate(inputdata):
        if linenum < 1:
            #header on first row
            continue
        # print('\n' + line.rstrip())

        try:
            result = mtch.fullmatch(line.rstrip()).groupdict()
        except Exception as ex:
            regexFails += 1
            print("failed to match: " + line + str(ex))
            continue
        result['time'] = float(result['time'])
        result['id'] = int(result['id'], 16)
        result['dlc'] = int(result['dlc'])
        inputDataList.append(result)
print(f"Parsed {len(inputDataList)} log lines")
#%% fix time
logStartTime = inputDataList[0]['time']
if logStartTime < 0:
    raise Exception("Start time is < 0!")

logEndTime = inputDataList[-1]['time']
if logEndTime < 0:
    raise Exception("End time is < 0!")

lastTime = logStartTime
lastGoodIndex = 0
index = 0
while index < len(inputDataList) - 1:
    # print(inputDataList[index])

    if inputDataList[index]['time'] < lastTime:
        print(f"time regression on line {index+1}! {logLineDict['time']:0.2f} {lastTime=:0.2f}")
        for searchIndex in range(index+1, len(inputDataList)):
            if inputDataList[searchIndex]['time'] > lastGoodTime:
                nextGoodTime = inputDataList[searchIndex]['time']
                nextGoodIndex = searchIndex
                print(f"Found good time {nextGoodTime:02f} on line {searchIndex+1}")
                break # end the search loop
        else:
            raise Exception("Could not find a good index after the time reg!")
        
        errorRegionDeltaT = nextGoodTime - lastGoodTime
        errorRegionDeltaI = nextGoodIndex - lastGoodIndex - 1
        print(f"Gap start line {lastGoodIndex+1}, end line {nextGoodIndex}, length {errorRegionDeltaT:.04f}s, {errorRegionDeltaI} frames")
        
        for replaceIndex in range(lastGoodIndex+1, nextGoodIndex):
            inputDataList[replaceIndex]['time'] = (replaceIndex-lastGoodIndex)*(errorRegionDeltaT/errorRegionDeltaI) + lastGoodTime

        # print(inputDataList[lastGoodIndex])
        # print(inputDataList[lastGoodIndex+1])
        # print(inputDataList[lastGoodIndex+2])
        # print(inputDataList[nextGoodIndex-2])
        # print(inputDataList[nextGoodIndex-1])
        # print(inputDataList[nextGoodIndex])
        # print(inputDataList[nextGoodIndex+1])
        ## setup for next region
        index = nextGoodIndex
    else:
        lastGoodTime = inputDataList[index]['time']
        lastGoodIndex = index


    index += 1
    # if (index % 10000) == 0:
        # print(f"Looking at index {index}")
print("Time fix complete.")
#%% output text file

outputFilePath, _ = os.path.splitext(fileLogPath)
outputFilePath += r'_recon'
with open(outputFilePath, "w") as outputFile:
    outputFile.write("s.us,id,dlc,data\n")
    for line in inputDataList:
        outputFile.write(f"{line['time']:.6f}%0x{line['id']:0X}:{line['dlc']}:{line['data']}\n")


#%% output csv

df = pandas.DataFrame(inputDataList, columns=headerlist)


outputFilePath, _ = os.path.splitext(fileLogPath)
outputFilePath += r'.csv'
df.to_csv(outputFilePath, index=False)
print("CSV saved to", outputFilePath)
# df
# %%

# %%
