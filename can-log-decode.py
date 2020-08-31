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
from si_prefix import si_format


configFolder = r".\configs"
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
    def __init__(self,id,checkBounds,datatype,maxValue,minValue,name,offset):
        self.id = id
        self.checkBounds = checkBounds
        self.dataTypeStr = datatype.rstrip()
        self.maxValue = maxValue
        self.minValue = minValue
        self.name = name
        self.offset = offset

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
            byteOffset = self.offset // 8
            self.datatype = bool
            self.dataWidth = 1
            self.parsestr = r'<' + r'x' * byteOffset + r'B' + r'x' * (8 - byteOffset - self.dataWidth)


    def parse(self, candata):
        if self.dataTypeStr == 'bit':
            mask = 2**(7 - (self.offset % 8))

            self.currentValue = self.datatype(struct.unpack(self.parsestr, candata)[0] & mask)
            
        else:
            self.currentValue = self.datatype(struct.unpack(self.parsestr, candata)[0])
    
    def __repr__(self):
        info = "{{\n\tid: {}\n\tcheck: {}\n\tdatatype: {}\n\t"
        info = info + "maxValue: {}\n\tminValue: {}\n\t"
        info = info + "name: {}\n\toffset: {}\n\t"
        info = info + "width = {}\n\t"
        info = info + "parsestr: {}\n}}"
        info = info.format(self.id, self.checkBounds, self.dataTypeStr,
            self.maxValue, self.minValue,  
            self.name, self.offset, self.dataWidth,
            self.parsestr)

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
            config.get('can_id', None),
            config.get('check_bounds', None),
            config.get('datatype', None),
            config.get('max_value', None),
            config.get('min_value', None),
            config.get('name', None),
            config.get('offset', None)
        ))

dlcs = []
headerlist = ['time']
headerstr = ""
for canid in sorted(database.items()):
    # print(canid, end='\n\n\n')
    highestByte = 0
    for datum in canid[1]:
        offset = datum.offset
        if datum.dataTypeStr == "bit":
            offset = offset / 8
        if (datum.dataWidth + offset) > highestByte:
            highestByte = datum.dataWidth + datum.offset

        headerlist.append(datum.name)
        headerstr = headerstr + datum.name + ", " 
    headerstr = headerstr[:-2] # remove trailing ,
    # if highestByte > 8:

    #     print(canid[0])
    # print(canid[0], highestByte)
    # dlcs[canid[0]] = highestByte
    dlcs.append(highestByte)
    
# print(headerstr)

#%% op


driveRoot = "J:"

logPath = driveRoot
#find folder
yearList = [x for x in os.listdir(logPath) if x.isdigit()]
year = sorted(yearList)[-1]
logPath += '\\' + year
monthList = [x for x in os.listdir(logPath) if x.isdigit()]
month = sorted(monthList)[-1]
logPath += '\\' + month
dayList = [x for x in os.listdir(logPath) if x.isdigit()]
day = sorted(dayList)[-1]
logPath += '\\' + day

fileName = sorted(os.listdir(logPath))[-1]
hour = int(fileName[0:2])
mininute = int(fileName[2:4])
seccond = int(fileName[4:6])

(year, month, day, hour, mininute, seccond, logPath, fileName)

fileLogPath = logPath + '\\' + fileName


# ptrn = r"\s*(?P<time>\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
ptrn = r"^\s*(?P<time>\d*.\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
mtch = re.compile(pattern=ptrn)
x = None
fails = 0
totalDropped = 0
tickRate = 100 # Hz
# with open("file.log") as inputdata:
firstTime = None
lastTime = None
times = []
outputLines = []
fakeLogRate = 5 # Create output log at this freq
fakeLogPeriod = 1/fakeLogRate
currentLogTime = 0
lastLogTime = 0
fakeLogCount = 0
print("Opening ", fileLogPath)
with open(fileLogPath) as inputdata:
    for linenum, line in enumerate(inputdata):
        if linenum < 1:
            #header on first row
            continue
        # print('\n' + line.rstrip())


        # skip fake IDNT arduino puts out
        
        try:
            result = mtch.fullmatch(line.rstrip()).groupdict()
        except Exception as ex:
            fails += 1
            print("failed to match: " + line + str(ex))
            continue

        time = float(result["time"])
        if not firstTime:
            firstTime = time
        if lastTime:
            times.append(time-lastTime)
        lastTime = time
        
        idnt = int(result["id"], 16)
        if idnt == 0x708 or idnt ==0x0:
            continue
        dlc = int(result["dlc"], 10)
        fulldata = []
        if dlc > 0:
            if result['data'].endswith(','):
                result['data'] = result['data'][:-1]
            try:
                fulldata = [int(x, 10) for x in result["data"].split(",")]
            except Exception as ex:
                print(ex)
        if dlc != len(fulldata):
            print("DLC mismatch!")


        if idnt not in database:
            print("idnt not found ", hex(idnt))
        
        # print("Frame: id={}, data={}".format(hex(idnt), fulldata))
        
        x = bytearray(fulldata)
        # parse each datum in the can data frame for this id
        for canObj in database[idnt]:
            # print("trying to parrse name = ", canObj.name)

            # print("type ", canObj.dataTypeStr, " off ", canObj.offset)
            canObj.parse(x)
            # print("got value: ", canObj.currentValue)


        # print the fake log
        currentLogTime = time
        if (currentLogTime - lastLogTime) > fakeLogPeriod:
            lastLogTime = currentLogTime
            # lineToLog = ""    
            numbersToLog = [currentLogTime]
            for canid in sorted(database.items()):
                for datum in canid[1]:
                    numbersToLog.append(datum.currentValue)
                    # lineToLog += str(datum.currentValue) + ","
            # lineToLog = lineToLog + "\n"
            outputLines.append(numbersToLog)
            fakeLogCount += 1
        


    



    timeTaken = (lastTime-firstTime)

    print(f"\nLog parse complete with {fails} parse errors of {linenum} frames.")
    print(f"Capture length: {datetime.timedelta(seconds=round(timeTaken))} hh:mm:ss.")
    print(f"Estimated log rate: {linenum/timeTaken:.1f} frames/s.")
    print(f"Created {fakeLogCount} CSV log entires.")

    mean = statistics.mean(times)
    stddev = statistics.stdev(times)
    median = statistics.median(times)
    print(f"\u0394t: mean = {si_format(mean)}s, median = {si_format(median)}s, stdev = {si_format(stddev)}s")

    plt.plot(times)


#%% output csv

df = pandas.DataFrame(outputLines, columns=headerlist)

df.to_csv(r"test.csv")

# df