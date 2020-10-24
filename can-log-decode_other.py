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
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import argparse
from si_prefix import si_format
import sys
import wget

#%% args
parser = argparse.ArgumentParser(description="Parse a SensorBoard can log")
parser.add_argument('inputFile', nargs='*', default=None, help="the can log to parse")
args = parser.parse_args()


#%% files
dirname = os.path.dirname(__file__)
configFolder = os.path.join(dirname, 'configs')

configUrl = r"https://solarracing.me/api/configs"
wget.download(configUrl, out=r'./configs/fetchedConfig.json')
configFolder = r"configs"
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
            self.bitMask = 2**(offset%8)
            self.offset = self.offset // 8
            self.datatype = bool
            self.dataWidth = 1
            self.parsestr = r'<' + r'x' * self.offset + r'B' + r'x' * (8 - self.offset - self.dataWidth)
        else:
            raise(Exception("Unknown type"))


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
        parseStr={self.parsestr}
        currentValue={self.currentValue}"""

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
args = {'inputFile': None}
args.inputFile = r"C:\Users\benlt\OneDrive\School\20211\Solar\incident\sd card\2020\08\19\221358"
if not args.inputFile:
    driveRoot = r"/media/ben/SENSORBOARD/"

    logPath = driveRoot
    #find folder
    yearList = [x for x in os.listdir(logPath) if x.isdigit()]
    year = sorted(yearList)[-1]
    logPath = os.path.join(logPath, year)
    monthList = [x for x in os.listdir(logPath) if x.isdigit()]
    month = sorted(monthList)[-1]
    logPath = os.path.join(logPath, month)
    dayList = [x for x in os.listdir(logPath) if x.isdigit()]
    day = sorted(dayList)[-1]
    logPath = os.path.join(logPath, day)

    filesInFolder = [x for x in os.listdir(logPath) if not x.endswith(".csv")]

    fileName = sorted(filesInFolder)[-1]
    hour = int(fileName[0:2])
    mininute = int(fileName[2:4])
    seccond = int(fileName[4:6])

    (year, month, day, hour, mininute, seccond, logPath, fileName)

    fileLogPath = os.path.join(logPath, fileName)
else:
    fileLogPath = args.inputFile


#%%
# fileLogPath = r"C:\Users\benlt\OneDrive\School\20211\Solar\incident\sd card\2020\08\19\221358_recon"
# fileLogPath = r"C:\Users\benlt\OneDrive\School\20211\Solar\incident\sd card\recon\221358_recon"
# fileLogPath = r"C:\temp\09\11\010958"
fileLogPath = r"C:\temp\sd card dump\2020\10\23\032822"
# ptrn = r"\s*(?P<time>\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
ptrn = r"^\s*(?P<time>\d*.\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
mtch = re.compile(pattern=ptrn)
x = None
fails = 0
firstTime = None
lastTime = None
times = []
arrivalTimes = {}
smoothFactor = 0.05
outputLines = []
unknownIds = set()
countsPerIdnt = {}
fakeLogRate = 10 # Create output log at this freq
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
            print(f"failed to match line {linenum}: " + line + str(ex))
            continue

        time = float(result["time"])
        if not firstTime:
            firstTime = time
        if lastTime:
            times.append(time-lastTime)
        lastTime = time
        
        idnt = int(result["id"], 16)
        countsPerIdnt[idnt] = countsPerIdnt.get(idnt, 0) + 1

        if idnt not in arrivalTimes:
            arrivalTimes[idnt] = []
        arrivalTimes[idnt].append(time)


        dlc = int(result["dlc"], 10)
        fulldata = []
        if dlc > 0:
            if result['data'].endswith(','):
                result['data'] = result['data'][:-1]
            try:
                fulldata = [int(x, 16) for x in result["data"].split(",")]
            except Exception as ex:
                print("failed while trying to get data array: ", ex)

        if dlc != len(fulldata):
            print(f"DLC mismatch on line {linenum}! CAN config may be incorrect.")


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
            lastLogTime = currentLogTime
            # lineToLog = ""    
            numbersToLog = [currentLogTime] + [None] * (len(headerlist)-1)

            # print("parsed", database[idnt])
            
            for datum in database[idnt]:
                # print(f"for idnt {idnt}, index is {headerlist.index(datum.name)}")
                numbersToLog[headerlist.index(datum.name)] = datum.currentValue
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
    print("Unknown IDs:", list(map(hex,sorted(unknownIds))))
    newSata = pandas.Series(times).rolling(window=int(len(times)/30)).mean()
    plt.rcParams.update({
        "figure.facecolor":  (1.0, 1.0, 1.0, 1),
        "axes.facecolor":    (1.0, 1.0, 1.0, 1),
        "savefig.facecolor": (1.0, 1.0, 1.0, 1),
        'figure.figsize' : [7,4]
    })
    fig, ax = plt.subplots()
    ax.set_xlabel("CAN log line number")
    ax.set_ylabel("Smoothed time between frames (s)")
    ax.set_title("Rolling mean time between consecutive frames")
    ax.grid(True)
    ax.plot(newSata)
    ax.set_xlim(0, len(times))
    plt.savefig("CAN_interframe_times")
    plt.show()


#%% preform stats on the arrival times
deltaTs = {}
deltaTstats = {}
for idnt in arrivalTimes:
    lastTime = arrivalTimes[idnt][0]
    deltaTs[idnt] = []
    for time in arrivalTimes[idnt][1:]:
        deltaTs[idnt].append(time-lastTime)
        lastTime = time
    deltaTstats[idnt] = {}
    deltaTstats[idnt]['mean']   = statistics.mean(deltaTs[idnt])
    deltaTstats[idnt]['stddev'] = statistics.stdev(deltaTs[idnt])
    deltaTstats[idnt]['median'] = statistics.median(deltaTs[idnt])


#%% Plot stats
def annotate(plt, canid, text = "", units="", xOffset = 1.5, yOffset = 1.5):
    if  text:
        plotText = text
    elif canid in database:
        names = [cfg.name for cfg in database[canid]]
        plotText = "\n".join(names)
    else:
        plotText = f"0x{canid:x}"
    if units:
        plotText = plotText + f" ({yvals[xvals.index(canid)]:0.1f} {units})"
    plt.annotate(plotText, xy=(xvals.index(canid), yvals[xvals.index(canid)]), 
        arrowprops=dict(facecolor='black', shrink=0.1),
        xytext=(xvals.index(canid)+xOffset, yvals[xvals.index(canid)]+yOffset))


xvals = []
yvals = []
colors = []
errorBars = []
colorConfigs = {
    'bms' : 'tab:blue',
    'sensorboard' : 'tab:purple',
    'rightWS' : 'tab:olive',
    'leftWS' : 'tab:green',
    'mc2' : 'tab:brown',
    'mppt' : 'tab:cyan',
    'other' : 'tab:grey'
}
patches = []
for key, value in colorConfigs.items():
    patches.append(mpatches.Patch(color=colorConfigs[key], label=key))
counts = {
    'bms' : 0,
    'sensorboard' : 0,
    'rightWS' : 0,
    'leftWS' : 0,
    'mc2' : 0,
    'mppt' : 0,
    'other' : 0
}
unitStr = "Hz"
errorCap = 10
for key in sorted(countsPerIdnt.keys()):
    xvals.append(key)
    yvals.append(countsPerIdnt[key]/timeTaken)
    error = deltaTstats[key]['stddev']
    if error > errorCap: error = errorCap
    errorBars.append(error)
    if key == 0x1 or (key >= 0x300 and key <= 0x34e):
        colors.append(colorConfigs['bms'])
        counts['bms'] += 1
    elif key == 0x69 or (key >= 0x7b1 and key <= 0x7c7):
        colors.append(colorConfigs['sensorboard'])
        counts['sensorboard'] += 1
    elif ((key >= 0x180 and key <= 0x181) 
        or (key >= 0x280 and key <= 0x281)
        or (key >= 0x480 and key <= 0x481)
        or (key >= 0x690 and key <= 0x695)):
        colors.append(colorConfigs['mppt'])
        counts['mppt'] += 1
    elif key >= 0x400 and key < 0x420:
        colors.append(colorConfigs['rightWS'])
        counts['rightWS'] += 1
    elif key >= 0x420 and key <= 0x437:
        colors.append(colorConfigs['leftWS'])
        counts['leftWS'] += 1
    elif key >= 0x501 and key <= 0x569:
        colors.append(colorConfigs['mc2'])
        counts['mc2'] += 1
    else:
        colors.append(colorConfigs['other'])
        counts['other'] += 1
plt.rcParams.update({
    "figure.facecolor":  (1.0, 1.0, 1.0, 1),
    "axes.facecolor":    (1.0, 1.0, 1.0, 1),
    "savefig.facecolor": (1.0, 1.0, 1.0, 1),
    'figure.figsize' : [20, 8],
    'figure.dpi' : 200
})
fig, ax = plt.subplots()

ax.bar(range(len(xvals)), yvals, align='center', color=colors, yerr=errorBars)
plt.xticks(range(len(xvals)), [hex(val) for val in xvals])
plt.xticks(rotation=75)
ymax = 5*round(max(yvals)/5)+10
plt.yticks(range(0,ymax, 5))
plt.ylim(0, ymax-5)
ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())
plt.xlabel('CAN ID')
plt.ylabel('frames/s')
startTimeStr = datetime.datetime.utcfromtimestamp(firstTime - 6*60*1000).strftime("%m/%d/%Y %H:%M:%S ET")
endTimeStr = datetime.datetime.utcfromtimestamp(time- 6*60*1000).strftime("%m/%d/%Y %H:%M:%S ET")
plt.title(f'Frequency of CAN IDs from {startTimeStr} to {endTimeStr} ({datetime.timedelta(seconds=round(timeTaken))} h:mm:ss)\n\nLarge variances capped to {errorCap}')
plt.grid(True, which='major', axis='y')
plt.grid(True, which='minor', alpha=0.25, axis='y')
plt.legend(('label1', 'label2', 'label3'))

annotate(plt, 0x403, "Right RPM", units=unitStr)
annotate(plt, 0x423, "Left RPM", units=unitStr)

annotate(plt, 0x437, units=unitStr)

plt.legend(handles=patches, loc=1)
plt.savefig('CAN_Freq', dpi=200, transparent=False)
plt.show()

vals = []
labels = []
colors = []
for key, value in counts.items():
    if value == 0: 
        continue
    vals.append(value)
    labels.append(key)
    colors.append(colorConfigs.get(key, 'tab:grey'))
plt.rcParams.update({
    "figure.facecolor":  (1.0, 1.0, 1.0, 1),
    "axes.facecolor":    (1.0, 1.0, 1.0, 1),
    "savefig.facecolor": (1.0, 1.0, 1.0, 1),
    'figure.figsize' : [4,4]
})
plt.pie(vals, colors=colors, labels=labels, autopct='%1.1f%%')
plt.rcParams['figure.dpi'] = 100 
plt.title(f'Percentage of frames counted over {datetime.timedelta(seconds=round(timeTaken))} h:mm:ss.')
plt.savefig('CAN_Pie', dpi=200, transparent=False)
plt.show()
#%% output csv

df = pandas.DataFrame(outputLines, columns=headerlist)


outputFilePath, _ = os.path.splitext(fileLogPath)
outputFilePath += r'_parsed.csv'
df.to_csv(outputFilePath, index=False)
print("CSV saved to", outputFilePath)
