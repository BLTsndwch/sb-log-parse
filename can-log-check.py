#! /usr/bin/python
#%% imports
import os
import re
import statistics
import matplotlib.pyplot as plt
from si_prefix import si_format
import datetime
from hurry.filesize import size





outputFreq = 10 # Hz
DEBUG = False


# teststr = r'0000567832%0x0056:8:AB,CD,EF,12,34,56,78,90'

if DEBUG:
    output = open("file.log", "w")
    for i in range(int(2**11 * 1.5)):
        line = "{:010d}%0x{:03X}:{}:".format(i+10000, i%(0x7FF+1), i%9)
        for j in range(i%9):
            line = line + "{:X},".format(j)
        line += "\n"
        output.write(line)
    output.close()



# ptrn = r"\s*(?P<time>\d*)\%(?P<id>0x[A-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>(([A-F0-9]{1,2})(?:\,?))*)"

# ptrn = r"\s*(?P<time>\d*)\%(?P<id>0x[A-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>(([A-F0-9]{1,2})(?:\,?))*)"

# ptrn = r"\s*(?P<time>\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
ptrn = r"^\s*(?P<time>\d*.\d*)\%(?P<id>0x[a-fA-F0-9]+)\:(?P<dlc>\d*)\:(?P<data>[a-zA-Z0-9,]*)"
mtch = re.compile(pattern=ptrn)


#%% decode

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

fileSize = os.path.getsize(logPath + "\\"  + fileName)

print("Checking ", logPath, fileName, "size: {}B".format(size(fileSize)))

lastID = None
fails = 0
totalDropped = 0
firstTime = None
lastTime = None
deltaTs = []
arrivalTimes = []
drops = []
dropDeltaTs = []
with open(logPath + "\\"  + fileName) as inputdata:
# with open(r"J:\TEMP\232957") as inputdata:
    for linenum, line in enumerate(inputdata):
        if linenum == 0:
            #header on first row
            continue
        # print('\n' + line.rstrip())

        # if linenum > 1000000:
        #     break

        
        try:
            result = mtch.fullmatch(line.rstrip()).groupdict()
        except Exception as ex:
            fails += 1
            print("failed to match: " + line + str(ex))
            continue

        time = float(result["time"])
        arrivalTimes.append(time)
        if not firstTime:
            firstTime = time
        if lastTime:
            deltaTs.append(time-lastTime)
        
        lastTime = time
        idnt = int(result["id"], 16)
        # dlc = int(result["dlc"], 10)
        # fulldata = []
        # if dlc > 0:
        #     if result['data'].endswith(','):
        #         result['data'] = result['data'][:-1]
        #     try:
        #         fulldata = [int(x, 10) for x in result["data"].split(",")]
        #     except Exception as ex:
        #         print(ex)
        # if dlc != len(fulldata):
        #     print("DLC mismatch!")
        dropped = 0
        if idnt != 0:
            if lastID is not None and (idnt-1) != lastID:
                #if 11 bit id rolls over, thats fine
                if not (idnt == 0x01 and lastID == 0x7FF):
                    if lastID > idnt:
                        dropped = (0x7FF - lastID) + (idnt - 2)
                    else:
                        dropped = idnt-lastID
                        
                    totalDropped += dropped
                    print(f"Lost an id on line {linenum:4d}! last=0x{lastID:03X} new=0x{idnt:03X} for {dropped} dropped.")
            lastID = idnt
        drops.append(dropped)


timeTaken = (lastTime-firstTime)
logDataRate_Bps = fileSize/timeTaken
print(f"\nLog check complete with {fails} parse errors of {linenum} frames.")
print(f"{totalDropped} frames were dropped (Success: {(1-(totalDropped/linenum))*100:.3f}%).")
print(f"Capture length: {datetime.timedelta(seconds=round(timeTaken))} hh:mm:ss.")
# print(f"Total capture time: {timeTaken:0.2f}s.")
print(f"Estimated log rate: {linenum/timeTaken:.1f} frames/s.")
print(f"Datarate: {size(logDataRate_Bps)}Bps or {size(logDataRate_Bps*8)}bps")

#%% delta t stats
mean = statistics.mean(deltaTs)
stddev = statistics.stdev(deltaTs)
median = statistics.median(deltaTs)
deltaTmax = max(deltaTs)
deltaTmin = min(deltaTs)
print(f"\u0394t: max = {si_format(deltaTmax)}s, min = {si_format(deltaTmin)}s, mean = {si_format(mean)}s, median = {si_format(median)}s, stdev = {si_format(stddev)}s")


plt.plot(deltaTs)
    
#%% Do math on dops
if sum(drops) > 0:
    dropsExist = True
else:
    dropsExist = False


if dropsExist:

    # drops = [x for x in drops if x != 0]
    # mean = statistics.mean(drops)
    # stddev = statistics.stdev(drops)
    # median = statistics.median(drops)
    print(f"drops: mean = {si_format(mean)}, median = {si_format(median)}, stdev = {si_format(stddev)}")
    plt.plot(drops)
else:
    print("no stats on drops if no drops :)")

#%%
if dropsExist:
    inds = [i for i,value in enumerate(drops) if value > 40]
    # lazy trigger holdoff
    edgeInds = []
    edgeInds.append(inds[0])
    for val in inds[1:]:
        if (val - edgeInds[-1]) > 40:
            edgeInds.append(val)

    bigDropDeltaTs = []
    lastInd = edgeInds[0]
    for edgeInd in edgeInds[1:]:
        bigDropDeltaTs.append( arrivalTimes[edgeInd] - arrivalTimes[lastInd] )
        lastInd = edgeInd



    # print(inds)
    # print(edgeInds)
    print("Time between large drops:", bigDropDeltaTs)
    mean = statistics.mean(bigDropDeltaTs)
    stddev = statistics.stdev(bigDropDeltaTs)
    median = statistics.median(bigDropDeltaTs)
    print(f"dropsDeltaT: mean = {si_format(mean)}, median = {si_format(median)}, stdev = {si_format(stddev)}")
else:
    print("no drop timing if no drops :)")

#%% try to find pattern in dops

if dropsExist:
    stopInd = len(drops)
    indDiffs = []
    for i in range(2, len(inds)):
        thisdiff = inds[i] - inds[i-1]
        if i < 50:
            print(i, inds[i], inds[i-1], thisdiff)
        indDiffs.append(thisdiff)

    mean = statistics.mean(indDiffs)
    stddev = statistics.stdev(indDiffs)
    median = statistics.median(indDiffs)
    print(f"drops: mean = {si_format(mean)}, median = {si_format(median)}, stdev = {si_format(stddev)}")
    plt.plot(indDiffs)
