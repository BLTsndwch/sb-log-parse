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
        self.parsestr = self.parsestr[:len(candata)+1]
        if self.dataTypeStr == 'bit':
            self.currentValue = self.datatype(struct.unpack(self.parsestr, candata)[0] & self.bitMask)
            
        else:
            try:
                self.currentValue = self.datatype(struct.unpack(self.parsestr, candata)[0])
            except Exception as ex:
                print("Failed to parse:", ex)
                print(f"{self.id}, {self.datatype}")
                print("\t", candata)
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
driveRoot = "D:"

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
firstTime = None
lastTime = None
times = []
outputLines = []
unknownIds = set()
countsPerIdnt = {}
fakeLogRate = 1 # Create output log at this freq
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
        countsPerIdnt[idnt] = countsPerIdnt.get(idnt, 0) + 1
        # if idnt == 0x708 or idnt ==0x0:
        #     continue
        dlc = int(result["dlc"], 10)
        fulldata = []
        if dlc > 0:
            if result['data'].endswith(','):
                result['data'] = result['data'][:-1]
            try:
                fulldata = [int(x, 16) for x in result["data"].split(",")]
            except Exception as ex:
                print("failed while trying to get data array: ", ex)
        # if linenum < 100 and len(fulldata) != 8:
        #     print(f"line{linenum} id{idnt} had less than 8")
        if dlc != len(fulldata):
            print(f"DLC mismatch on line {linenum}!")
        # if linenum < 100 and dlcs.get(idnt) and dlc != dlcs[idnt]:
        #     print(f"calc DLC mismatch on line {linenum}! Id {idnt} Expect {dlcs[idnt]} got {dlc}")

        if idnt not in database:
            # print("idnt not found", hex(idnt))
            # print("Frame not in database: id={}, data={}".format(hex(idnt), fulldata))
            unknownIds.add(idnt)
        else:
            x = bytearray(fulldata)
            # parse each datum in the can data frame for this id
            for canObj in database[idnt]:
                # print("trying to parrse name = ", canObj.name)

                # print("type ", canObj.dataTypeStr, " off ", canObj.offset)
                # try:
                canObj.parse(x)
                # except Exception as ex:
                #     print(f"fail to parse line {linenum}:",ex, line)
                #     pass
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

    print("Unknown IDs:", list(map(hex,sorted(unknownIds))))


#%% output csv

df = pandas.DataFrame(outputLines, columns=headerlist)

df.to_csv(r"test.csv", index=False)
print("CSV saved.")
# df
# %%

# %%
