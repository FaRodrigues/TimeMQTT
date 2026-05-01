import subprocess
import serial  # pySerial
import serial.tools.list_ports
import time
import io
from subprocess import Popen, PIPE
import itertools
import numpy as np

optionsAlarm = np.array([1, 2, 4, 8, 16, 32, 64, 128])
descAlarm = np.array(
    ["External reference error", "Internal oscillator error", "PLL Lock error", "Tuning voltage error",
     "Invalid parameter", "Invalid command", "DC Backup Loss", "AC Power Loss"])

# Opções de alarme definidas no manual do HROG
optionsAlarmDict = {
    "External reference error": 1,
    "Internal oscillator error": 2,
    "PLL Lock error": 4,
    "Tuning voltage error": 8,
    "Invalid parameter": 16,
    "Invalid command": 32,
    "DC Backup Loss": 64,
    "AC Power Loss": 128
}


def findsubsets(s, n):
    return list(itertools.combinations(s, n))


ser = serial.Serial()


def checkIfComPorts():
    ports = serial.tools.list_ports.comports()
    rc = "HROG not found"
    HROG_PORT = ""
    for port in ports:
        id = port.hwid
        print(f"Device: {port.device}")
        print(f"Description: {port.description}")
        print(f"Hardware ID: {id}\n")
        if "HROG" in str(id):
            HROG_PORT = port.device
            rc = "HROG found"
    return [HROG_PORT, rc]


def initializeComport(port):
    ser.baudrate = 9600
    ser.port = port
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    ser.timeout = 0.1


def setCommand(command):
    if not (ser.isOpen()):
        print("Abrindo a porta: {}".format(ser.portstr))
        ser.open();
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
    sio.write("{}\n".format(command))


def queryInstrument(gc):
    if not (ser.isOpen()): ser.open()
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
    sio.write("{}\n".format(gc))
    # it is buffering. required to get the data out *now*
    sio.flush()
    result = sio.readlines()
    print(result)
    tamresp = len(result)
    if tamresp > 0:
        query = result[tamresp - 2].replace(gc, '').replace('\\n', '')
    else:
        query = None
    # print(query)
    return query


optionsAlarm = []


# def indexOfList(x):
#     # Opções de alarme definidas no manual do HROG
#     # optionsAlarm = [1, 2, 4, 8, 16, 32, 64, 128]
#     optionsAlarmDict = {"External reference error": 1, "Internal oscillator error": 2, "PLL Lock error": 4, "Tuning voltage error": 8,
#      "Invalid parameter": 16, "Invalid command": 32, "DC Backup Loss": 64, "AC Power Loss": 128}
#     optionsAlarm = list(optionsAlarmDict.values())
#     return optionsAlarm.index(x)

def indexOfList(x):
    valorindex = []
    optionsAlarm = list(optionsAlarmDict.values())
    subsetsresp = findsubsets(optionsAlarm, 4)
    subsetsrespsummatch = list(map(sum, subsetsresp)).index(x)
    try:
        valorindex = optionsAlarm.index(x)
    except:
        print("ERRO: NÃO foi encontrado índice para o valor [ {} ]".format(x))
    return valorindex


def indexListOfAlarmsByCode(errcode):
    listaresp = []
    alarmePOS = []
    for x in range(8):

        optionsAlarm = list(optionsAlarmDict.values())
        chaves = np.array(list(optionsAlarmDict.keys()))

        def getindexes(x):
            return optionsAlarm.index(x)

        # Gera subsets de optionsAlarm com tamanho 4
        subsetsresp = findsubsets(optionsAlarm, x)
        # print(subsetsresp)

        try:
            subsetsrespsummatch = list(map(sum, subsetsresp)).index(errcode)
        except:
            subsetsrespsummatch = -1

        if (subsetsrespsummatch > -1):
            # print(subsetsrespsummatch)
            alarmeID = list(subsetsresp[subsetsrespsummatch])
            alarmePOS = list(map(getindexes, alarmeID))
            listaresp = list(chaves[alarmePOS])

    return listaresp


def main():
    optionsAlarm = []
    descAlarm = []
    resp = checkIfComPorts()
    status_message = resp[1]
    print(f"Status Message = {status_message}")
    hrog_port = resp[0]
    if "COM" in hrog_port and len(hrog_port) > 0:
        initializeComport(hrog_port)
        print(queryInstrument('ID'))
        setCommand('MODE 2')
        print(queryInstrument('MODE?'))
        time.sleep(1)
        print(queryInstrument('MODE?'))
        setCommand('FREQ -0.5237')
        # print(queryInstrument('PHAS?'))
        # print(queryInstrument('TEMP?'))
        # print(queryInstrument('TIME?'))
        # errcode = queryInstrument('*SRE')
        # errcodeDESCS = indexListOfAlarmsByCode(int(errcode))
        # print(errcodeDESCS)
        # setCommand('*CLS')
        # setCommand('SFREQ 7.31265')
    else:
        print("--> ERRO: {}".format(status_message))


if __name__ == "__main__":
    main()
