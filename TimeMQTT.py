import io
import itertools
import math
import os
import sys
from collections import deque
from threading import Event

import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QThread, QFile, QRect, Qt, QDate, QDateTime, QTime
from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection
from PySide6.QtGui import QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QApplication, QLabel, QLCDNumber, QDateTimeEdit, QPushButton, QComboBox, QLineEdit
from astropy.time import Time
from datetime import datetime as dtime, timedelta
import time as timenative

from quantiphy import Quantity
import serial  # pySerial
import serial.tools.list_ports

ser = serial.Serial()

def checkIfComPorts():
    rc = "HROG not found"
    ports = serial.tools.list_ports.comports()
    print(f"==> All Ports: {ports}")
    HROG_PORT = ""
    for port in ports:
        id = port.hwid
        print(f"Device: {port.device}")
        print(f"Description: {port.description}")
        print(f"Hardware ID: {id}\n")
        if "HROG" in str(id):
            HROG_PORT = port.device
            rc = f"HROG found in port {HROG_PORT}!"
    return [HROG_PORT, rc]

def initializeComport(port):
    ser.baudrate = 9600
    ser.port = port
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    ser.timeout = 0.1

def getDateFromMJD(MJD):
    tmjd = Time(MJD, format='mjd')
    stringdate = Time(tmjd.to_value('iso'), out_subfmt='date').iso
    return QDate.fromString(str(stringdate), "yyyy-MM-dd")


def getDateTimeFromNow():
    t1 = Time(dtime.now())
    stringdate = Time(t1.to_value('iso'), out_subfmt='date_hms').iso
    dt = dtime.fromisoformat(stringdate)
    qdatetime = QtCore.QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    return qdatetime


def findsubsets(s, n):
    return list(itertools.combinations(s, n))


def getEmbededObjet(self, tipo, nome):
    search = self.findChildren(tipo, nome)
    objeto = search[0]
    # print("objeto = {}".format(objeto))
    return objeto


def getMJDFracFromTime(delta):
    t0 = timedelta(hours=delta)
    t1 = Time(dtime.now() + t0)
    tmjd = t1.to_value('mjd', subfmt='float')
    # print(tmjd)
    return tmjd


def getContextMJD():
    fracout, intNumout = math.modf(getMJDFracFromTime(0))
    contextmjdlocal = int(intNumout)
    return contextmjdlocal


def getSubDividedDayTime(nowqdtime, localbasetime, instep):
    nowdate = nowqdtime.date()
    sddt = []
    starttime = QTime(00, 00)
    stoptime = QTime(23, 59)
    deltastart = starttime.secsTo(starttime)
    deltastop = starttime.secsTo(stoptime)
    basedelta = localbasetime.secsTo(stoptime)
    if instep > 0:
        try:
            outstep = round((deltastop - deltastart) / instep)
            resp1 = list(range(round(deltastart), round(deltastop), outstep))
            # print(resp1)
            for h in resp1:
                dayslice = round(h + outstep - basedelta)
                if dayslice >= 0:
                    timelocal = starttime.addSecs(dayslice)
                    qdt = QDateTime()
                    qdt.setDate(nowdate)
                    qdt.setTime(timelocal)
                    sddt.append(qdt)
        except:
            print("Não foi possível gerar a lista de horários")
    return sddt


class UserInterfaceHROG(QMainWindow):
    def __init__(self):
        super(UserInterfaceHROG, self).__init__()
        self.nextScheduledDatetime = None
        self.datetimeToDoTask = None
        self.qdtnow = getDateTimeFromNow()
        self.scheduledValue = None
        self.lastscheduledDatetime = 0
        self.listOfFixedTime = getSubDividedDayTime(self.qdtnow, QTime(22, 20), 4)
        self.ser = None
        self.contextmjd = None
        self.basetimetoschedule = None
        self.optionsAlarm = None
        self.scheduledValue = None
        self.chaves = None
        self.portaSEL = None
        self.opwindow = None
        self.optime = None
        self.ophum = None
        self.optemp = None
        self.opport = None
        self.opid = None
        self.opalarm = None
        self.opvalue = None
        self.optoken = None
        self.activeFreqOffset = 0
        self.estrategCorr = 0
        self.tokenHROGPORT = None
        self.activeFreqOffset = 0
        self.lastVMvalue = None
        self.contextSlope = None
        self.daysinterval = None
        self.DRCGG = None
        self.lastFreqCorrCalculated = None
        self.lastFreCorrected = None
        self.dataprocesstoken = None
        self.newcorrectiontoken = False
        self.dataprocesstoken = False
        self.thread = QThread()
        self.HROGWidget = None

        resp = checkIfComPorts()
        status_message = resp[1]
        # print(f"Status Message = {status_message}")
        hrog_port = resp[0]
        if "COM" in hrog_port and len(hrog_port) > 0:
            initializeComport(hrog_port)
        else:
            print("==> ERR: {}".format(status_message))

        loader = QUiLoader()
        guipath = os.path.abspath(os.path.join("gui", "ui", "formHROGEn.ui"))
        file = QFile(guipath)
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file, self)
        file.close()

        self.statusbar = self.statusBar()
        self.statusbar.setFont(QtGui.QFont('Arial', 10, QFont.Weight.DemiBold))
        self.statusbar.setSizeGripEnabled(False)

        self.setWindowTitle("HROG-10 Interactive Interface Sample")

        self.groupBox3Text = getEmbededObjet(self, QLabel, "labelEquipIdent")
        self.groupBox4Text = getEmbededObjet(self, QLabel, "labelPortIdent")

        self.labelUNITFREQCORROP = getEmbededObjet(self, QLabel, "labelNumberFREQ")
        self.sevenSEGMENTSERRO = getEmbededObjet(self, QLCDNumber, "lcdNumberERRO")
        self.sevenSEGMENTSFREQCORROP = getEmbededObjet(self, QLCDNumber, "lcdNumberFREQ")

        self.dateTimeEditOP = getEmbededObjet(self, QDateTimeEdit, "dateTimeEdit")

        self.sevenSEGMENTSFREQCORRAG = getEmbededObjet(self, QLCDNumber, "lcdNumberFREQAG")
        self.labelUNITFREQCORRAG = getEmbededObjet(self, QLabel, "labelNumberFREQAG")
        self.dateTimeEditAG = getEmbededObjet(self, QDateTimeEdit, "dateTimeEditAG")

        self.labelEquipIdent = getEmbededObjet(self, QLabel, "labelEquipIdent")
        self.labelPortIdent = getEmbededObjet(self, QLabel, "labelPortIdent")

        self.labelLabTemp = getEmbededObjet(self, QLabel, "labelLabTemp")
        self.labelLabHum = getEmbededObjet(self, QLabel, "labelLabHum")

        self.pushButtonEst = getEmbededObjet(self, QPushButton, "pushButtonEst")
        self.pushButtonEst.clicked.connect(self.applyLocalFreqCorr)

        listaEstrategCorr = {1: "Fixed Time", 2: "Fixed Interval", 3: "Manual"}
        self.comboBoxEst = getEmbededObjet(self, QComboBox, "comboBoxEst")
        self.comboBoxEst.addItems(listaEstrategCorr.values())
        self.comboBoxEst.activated.connect(self.defineEstrategCorr)
        # creating a line edit
        combolinedit = QLineEdit(self)
        # setting line edit
        self.comboBoxEst.setLineEdit(combolinedit)
        line_edit = self.comboBoxEst.lineEdit()
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stateDictProposedAG = {
            "agtoken": self.optoken,
            "agvalue": self.opvalue,
            "agalarm": self.opalarm,
            "agid": self.opid,
            "agport": self.opport,
            "agtemp": self.optemp,
            "aghum": self.ophum,
            "agtime": self.optime
        }

        self.stateDictOP = {
            "optoken": self.optoken,
            "opvalue": self.opvalue,
            "opalarm": self.opalarm,
            "opid": self.opid,
            "opport": self.opport,
            "optemp": self.optemp,
            "ophum": self.ophum,
            "optime": self.optime,
            "opwindow": self.opwindow
        }

        # Opções de alarme descritas no manual do equipamento e definidas no código na forma de um dict
        self.optionsAlarmDict = {
            1: "External reference error",
            2: "Internal oscillator error",
            4: "PLL Lock error",
            8: "Tuning voltage error",
            16: "Invalid parameter",
            32: "Invalid command",
            64: "DC Backup Loss",
            128: "AC Power Loss"
        }

        self.chaves = list(self.optionsAlarmDict.keys())
        self.valores = list(self.optionsAlarmDict.values())
        self.atualizaAlarmeMonitor([], True)

        # Atualiza a interface
        # self.atualizaDisplayOP()
        # self.displayErrorCodeForRemoteAG(0)

    def atualizaStatusBar(self, basemessage, cor):
        try:
            message = f"Status | {basemessage}"
            self.statusbar.showMessage(message)
            stylelocal = "QStatusBar {{background-color: {}; color: white; border: 1px solid blue; font-weight:normal}}"
            style = stylelocal.format(cor)
            self.statusbar.setStyleSheet(style)
            QtCore.QCoreApplication.processEvents()
        except:
            pass

    def applyLocalFreqCorr(self):
        respvalue, success = self.scheduledValue, False
        print("Aplicando o valor de correção  = {}".format(self.scheduledValue))
        try:
            respvalue, success = self.setTransactCommand("FREQ {}".format(self.scheduledValue), "FREQ?")
        except:
            pass

    def defineEstrategCorr(self, est):

        print(f"est = {est}")
        self.estrategCorr = est

        if est == 2:
            self.pushButtonEst.setEnabled(True)
            self.pushButtonEst.setStyleSheet("background-color: rgb(255, 170, 0);")
        else:
            if est == 0:
                datetimenow = getDateTimeFromNow()
                self.getUpdatedTimerSchedule(datetimenow)

            self.pushButtonEst.setEnabled(False)
            self.pushButtonEst.setStyleSheet("background-color: rgb(128, 128, 128);")

    def atualizaDisplayOP(self):
        freqcorr = self.activeFreqOffset
        # Query frequency offset
        if self.tokenHROGPORT:
            try:
                freqcorr = self.getHROGFreqOffSet()
            except:
                pass
        freqcorr = Quantity(freqcorr, 'Hz')
        freqcorrsplit = str(freqcorr).split(" ")
        # print("freqcorrsplit = {}".format(freqcorrsplit))
        self.sevenSEGMENTSFREQCORROP.display(freqcorrsplit[0])
        self.labelUNITFREQCORROP.setText(freqcorrsplit[1])
        datetimeOP = getDateTimeFromNow()  # self.getDateTimeFromMJDFrac(timestamp)
        self.dateTimeEditOP.setDisplayFormat("[ HH:mm ] dd/MM/yyyy")
        self.dateTimeEditOP.setDateTime(datetimeOP)

        usedport = self.stateDictOP['opport']

        try:
            try:
                idequip = self.queryInstrumentID()
                self.stateDictOP['opid'] = idequip
            except:
                idequip = self.stateDictOP['opid']

            self.labelEquipIdent.setText(self.stateDictOP['opid'])

            if len(list(self.portaSEL)) > 0:
                usedport = list(self.portaSEL)[0]

            self.stateDictOP['opport'] = usedport
            self.labelPortIdent.setText(self.stateDictOP['opport'])

            self.stateDictOP['optemp'] = self.optemp
            self.labelLabTemp.setText('{} ºC'.format(self.stateDictOP['optemp']))

            self.stateDictOP['ophum'] = self.ophum
            self.labelLabHum.setText('{} %'.format(self.stateDictOP['ophum']))

        except ValueError as ex:
            pass

        QtCore.QCoreApplication.processEvents()

    def atualizaDisplayAG(self, se):
        # print("se = {} | dictrec = {}".format(se, dictrec))
        print("self.stateDictProposedAG['agtoken'] = {}".format(self.stateDictProposedAG['agtoken']))
        # if self.stateDictProposedAG['agtoken']:
        datetimeAG = self.nextScheduledDatetime
        print("datetimeAG = {}".format(datetimeAG))
        self.dateTimeEditAG.setDisplayFormat("[ HH:mm ] dd/MM/yyyy")
        self.dateTimeEditAG.setDateTime(datetimeAG)
        self.sevenSEGMENTSFREQCORRAG.display(self.stateDictProposedAG['agvalue'])
        self.labelUNITFREQCORRAG.setText('uHz')
        #
        # if se == True:
        #     cor = "rgb(255,255,255)"
        # else:
        #     cor = "rgb(255,170,0)"
        #
        # stylelocal = ("background-color: {};")
        # style = stylelocal.format(cor)
        # self.dateTimeEditAG.setStyleSheet(style)
        # time.sleep(0.05)
        # self.sevenSEGMENTSFREQCORRAG.setStyleSheet(style)
        # time.sleep(0.05)
        # self.labelUNITFREQCORRAG.setStyleSheet(style)
        # else:
        # self.dateTimeEditAG.setEnabled(False)
        QtCore.QCoreApplication.processEvents()

    def getHROGFreqOffSet(self):
        rawfreqcorr, se = self.queryInstrument('FREQ?')
        freqcorr = Quantity(rawfreqcorr, 'Hz')
        return freqcorr

    def queryInstrumentID(self):
        gc = "ID"
        if not (self.ser.isOpen()): self.ser.open()
        sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser))
        sio.write("{}\n".format(gc))
        # it is buffering. required to get the data out *now*
        sio.flush()
        result = sio.readlines()
        # print(result[0])
        tamresp = len(result)
        if tamresp > 0:
            query = result[tamresp - 2].replace(gc, '').replace('\n', '')
        else:
            query = None
        return query

    def queryInstrument(self, gc):
        tokensuccess = False
        if not (self.ser.isOpen()):
            self.ser.open()
        sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser))
        sio.write("{}\n".format(gc))
        # it is buffering. required to get the data out *now*
        sio.flush()
        result = sio.readlines()
        # print(result)
        tamresp = len(result)
        if tamresp > 0:
            query = result[tamresp - 2].replace(gc, '').replace('\n', '')
            tokensuccess = True
        else:
            query = " "
        # print(query)
        return query, tokensuccess

    def returnListOfAlarmsByCode(self, errcode):
        global alarmeID
        respostacheia = deque([])
        respostavazia = []

        for x in range(8):

            def getindexes(x):
                return self.chaves.index(x)

            def findsubsets(s, n):
                return list(itertools.combinations(s, n))

            # Gera subsets de optionsAlarm com tamanho 4
            subsetsresp = findsubsets(self.chaves, x)
            # print("subsetsresp = {}".format(subsetsresp))

            try:
                mapaiterativo = list(map(sum, subsetsresp))
                # print("mapaiterativo = {}".format(mapaiterativo))
                subsetsrespsummatch = list(mapaiterativo).index(errcode)
                # print("subsetsrespsummatch = {}".format(subsetsrespsummatch))
            except:
                subsetsrespsummatch = -1

            if (subsetsrespsummatch > -1):
                # print(subsetsrespsummatch)
                alarmeID = list(subsetsresp[subsetsrespsummatch])
                # print("alarmeID = {}".format(alarmeID))
                respostacheia.append(alarmeID)
                alarmePOS = list(map(getindexes, alarmeID))
                # print("alarmePOS = {}".format(alarmePOS))
                respostacheia.append(alarmePOS)
                listaresp = list(np.array(self.valores)[alarmePOS])
                # print("listaresp = {}".format(listaresp))
                respostacheia.append(listaresp)
                self.atualizaAlarmeMonitor(alarmeID, False)
                return respostacheia
        return respostavazia

    def indexListOfAlarmsByCode(self, errcode):
        # global alarmeID, listaresp, alarmePOS
        global listaresp, alarmeID, alarmePOS

        for x in range(8):

            def getindexes(item):
                return self.optionsAlarm.index(item)

            def getitembychave(ch):
                return self.chaves[ch]

            # Gera subsets de optionsAlarm com tamanho 4
            subsetsresp = findsubsets(self.optionsAlarm, x)
            # print(subsetsresp)
            try:
                subsetsrespsummatch = list(map(sum, subsetsresp)).index(errcode)
            except:
                subsetsrespsummatch = -1

            if subsetsrespsummatch > -1:
                # print(subsetsrespsummatch)
                alarmeID = list(subsetsresp[subsetsrespsummatch])
                alarmePOS = list(map(getindexes, alarmeID))
                listaresp = list(map(getitembychave, alarmePOS))
                self.atualizaAlarmeMonitor(alarmeID, False)
                # return
        return [listaresp, alarmeID, alarmePOS]

    def setTransactCommand(self, param, param1):
        pass

    def atualizaAlarmeMonitor(self, alarmeID, inicia):
        label = " "
        for chave in self.chaves:
            try:
                label = getEmbededObjet(self.ui, QLabel, str("label_{}").format(chave))
                timenative.sleep(0.05)
                if chave in alarmeID:
                    label.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    if inicia:
                        label.setStyleSheet("background-color: rgb(255, 255, 255);")
                    else:
                        label.setStyleSheet("background-color: rgb(128, 255, 128);")
            except:
                pass

    def getUpdatedTimerSchedule(self, now):
        difftimetofinal = now.time().secsTo(self.basetimetoschedule)
        fimdodiatoken = difftimetofinal < 0
        print("fimdodiatoken = {}\ndifftimetofinal = {}".format(fimdodiatoken, difftimetofinal))
        verifiedcontextmjd = getContextMJD()

        if verifiedcontextmjd > self.contextmjd or fimdodiatoken:
            self.contextmjd = verifiedcontextmjd
            self.listOfFixedTime = getSubDividedDayTime(now.addDays(1), self.basetimetoschedule, 4)
            print("Gerando nova lista de horários para agendamento.\n{}".format(self.listOfFixedTime))

        for qdtlocal in self.listOfFixedTime:
            # print("qdtlocal.secsTo(now) = {}".format(qdtlocal.secsTo(now)))
            if qdtlocal.secsTo(now) <= 0:
                self.datetimeToDoTask = qdtlocal
                self.nextScheduledDatetime = qdtlocal
                self.atualizaDisplayAG(False)
                return qdtlocal


StyleSheet = '''
QMainWindow {
    border: 1px solid blue;
    font-weight:bold
}
QMenuBar {
    background-color: #F0F0F0;
    color: #000000;
    border: 1px solid #000;
    font-weight:bold
}
QMenuBar::item {
    background-color: rgb(49,49,49);
    color: rgb(255,255,255)
}
QMenuBar::item::selected {
    background-color: rgb(30,30,30)
}
QTabWidget {
    background-color: #F0F0F0;
    border: 1px solid blue;
    border-radius: 20px
}
QTabWidget::pane {
    border: 1px solid #31363B;
    padding: 2px;
    margin:  0px
}
QTableView {
    selection-background-color: #0088cc
}
QTabBar {
    border: 0px solid #31363B;
    color: #152464
}
QTabBar::tab:top:selected {
    background-color: #0066cc;
    color: white
}
QCalendarWidget{
    border: 2px solid black;
    background-color: rgb(255,255,255)
}
QComboBox {
    border: 1px solid black;
}
QGroupBox {
    border: 2px solid gray;
    border-radius: 4px;
    margin-top: 16px
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px
}
'''
if __name__ == '__main__':
    # os.environ['PYSIDE_DESIGNER_PLUGINS'] = "."
    # QPyDesignerCustomWidgetCollection.registerCustomWidget(QWidget, module="formHROGWidget")
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_Use96Dpi, True)
    # QtCore.QCoreApplication.setAttribute( QtCore.Qt.ApplicationAttribute.AA_PluginApplication)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_ForceRasterWidgets)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_NativeWindows)
    app = QApplication(sys.argv)
    QPyDesignerCustomWidgetCollection.instance()
    styles = ["Plastique", "Cleanlooks", "CDE", "Motif", "GTK+"]
    app.setStyle(QtWidgets.QStyleFactory.create(styles[1]))
    app.setStyleSheet(StyleSheet)
    # app.setFont(QtGui.QFont("Arial", 11, QtGui.QFont.Bold))
    app_icon = QtGui.QIcon()
    app_icon.addFile(os.path.join('gui', 'icons', 'inmetro.ico'), QtCore.QSize(256, 256))
    app.setWindowIcon(app_icon)
    rect = QRect(200, 200, 800, 400)
    window = UserInterfaceHROG()
    window.setGeometry(rect)
    window.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
    # print("lastvalue = {}".format(dir(UserInterfaceDmtic)))
    window.show()
    app.exec()
