# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OrthoMaker
                                 A QGIS plugin
 Pluginn to calculate orthophotos from images and a DEM
                              -------------------
        begin                : 2016-03-15
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Andrew Flatman / sdfe.dk
        email                : anfla@sdfe.dk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import getpass
import socket

import ftools_utils
import sys
import math
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from ortho_maker_dialog import OrthoMakerDialog
from ortho_maker_file_dialog import OrthoMakerFileDialog
from ortho_maker_settings import OrthoMakerSettings, OrthoMakerSettingsDialog
import os.path

import remote_sensing as rs

class OrthoMaker:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'OrthoMaker_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = OrthoMakerDialog()
        self.fdl = OrthoMakerFileDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Ortho Maker')

        self.toolbar = self.iface.addToolBar(u'OrthoMaker')
        self.toolbar.setObjectName(u'OrthoMaker')

        # Settings dialog etc.
        self.settings = OrthoMakerSettings()
        self.settings_dlg = OrthoMakerSettingsDialog(self.settings)

        self.dlg.pushButton_Input.clicked.connect(self.showFileSelectDialogInput)
        self.dlg.pushButton_Output.clicked.connect(self.showFileSelectDialogOutput)
        self.fdl.pushButton_Output.clicked.connect(self.showFileSelectDialogOutputf)
        self.dlg.pushButton_workdir.clicked.connect(self.showFileSelectDialogWorkdir)
        self.dlg.pushButton_DEM.clicked.connect(self.showFileSelectDialogDEM)

        self.dlg.inDir.setText('C:/')
        self.dlg.outDir.setText('C:/temp/COWStemp/jpeg/')
        self.dlg.lineEditDEM.setText('F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt')
        self.dlg.lineEdit_workdir.setText('C:/Temp/COWStemp/')
        self.dlg.lineEditPixelSize.setText('0.16')
        self.dlg.lineEditImageAngle.setText('15')
        self.dlg.radioButtonDEM_2015.toggle()
        self.dlg.radioButton_fieldpath.toggle()
        self.dlg.checkBoxDelTiff.setCheckState(Qt.Checked)

        self.fdl.outDir.setText('F:/GEO\DATA/RemoteSensing/Drift/ForaarsFoto/FotoFlyv_2017/QuickOrto')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OrthoMaker', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def update1(self, inputLayer):
        self.dlg.inField1.clear()
        changedLayer = ftools_utils.getVectorLayerByName(unicode(inputLayer))
        changedField = ftools_utils.getFieldList(changedLayer)
        for f in changedField:
            if f.type() == QVariant.Int or f.type() == QVariant.String:
                self.dlg.inField1.addItem(unicode(f.name()))

    def update_ortonamefield(self, inputLayer):
        self.dlg.ortonamefield.clear()
        changedLayer = ftools_utils.getVectorLayerByName(unicode(inputLayer))
        changedField = ftools_utils.getFieldList(changedLayer)
        for f in changedField:
            if f.type() == QVariant.Int or f.type() == QVariant.String:
                self.dlg.ortonamefield.addItem(unicode(f.name()))

    def showFileSelectDialogInput(self):
        self.dlg.radioButton_txtpath.toggle()
        fname = QFileDialog.getOpenFileName(None, 'Read File', self.dlg.inDir.text(),
                                            'TIF file (*.tif);;All files (*.*)')
        self.dlg.inDir.setText(fname)

    def showFileSelectDialogOutput(self):
        fname = QFileDialog.getExistingDirectory(None, 'Select output directory', str(self.dlg.outDir.text()))
        self.dlg.outDir.setText(fname)

    def showFileSelectDialogWorkdir(self):
        fname = QFileDialog.getExistingDirectory(None, 'Select working directory',
                                                 str(self.dlg.lineEdit_workdir.text()))
        self.dlg.lineEdit_workdir.setText(fname)

    def showFileSelectDialogDEM(self):
        fname = QFileDialog.getOpenFileName(None, 'Select DEM file', self.dlg.lineEditDEM.text(),
                                            'TIF file (*.tif);;All files (*.*)')
        self.dlg.lineEditDEM.setText(fname)

    def showFileSelectDialogOutputf(self):
        fname = QFileDialog.getExistingDirectory(None, 'Select output directory', str(self.fdl.outDir.text()))
        self.fdl.outDir.setText(fname)

    def checkA(self):
        inputFilNavn = unicode(self.dlg.inShapeA.currentText())
        canvas = self.iface.mapCanvas()
        allLayers = canvas.layers()

        for i in allLayers:
            if (i.name() == inputFilNavn):
                if i.selectedFeatureCount() != 0:
                    self.dlg.useSelectedA.setCheckState(Qt.Checked)
                else:
                    self.dlg.useSelectedA.setCheckState(Qt.Unchecked)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/OrthoMaker/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Calculate Ortho Photos'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

        icon_path = ':/plugins/OrthoMaker/fld.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Build File List'),
            callback=self.build_filelist,
            parent=self.iface.mainWindow()
        )

        self.add_action(
            None,
            text=self.tr(u'Settings'),
            add_to_toolbar=False,
            callback=self.open_settings,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Ortho Maker'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def open_settings(self):
        self.settings_dlg.show()


    def run(self):
        #*** New Ortomaker ***
        self.dlg.show()

        CHKuser = getpass.getuser()
        maskinenavn = (socket.gethostname())
        basepath = 'F:\\JOB\\DATA\\RemoteSensing\\Drift\\GRU\\orto_bat_files\\'

        QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.checkA)
        QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.update1)
        QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.update_ortonamefield)
        self.dlg.setWindowTitle(self.tr("Make Ortho"))
        # populate layer list
        self.dlg.progressBar.setValue(0)
        mapCanvas = self.iface.mapCanvas()
        lyrs = self.iface.legendInterface().layers()
        lyr_list = []
        for layer in lyrs:
            lyr_list.append(layer.name())
        self.dlg.inShapeA.clear()
        self.dlg.inShapeA.addItems(lyr_list)

        self.dlg.progressBar.hide()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # See if OK was pressed
            if result:

                inputFilNavn = self.dlg.inShapeA.currentText()
                canvas = self.iface.mapCanvas()
                allLayers = canvas.layers()

                for i in allLayers:
                    # QMessageBox.information(None, "test input", i.name())
                    if (i.name() == inputFilNavn):
                        layer = i

                        # QMessageBox.information(None, "type", str(layer.geometryType()))
                        if (layer.geometryType() == 2):
                            # QMessageBox.information(None,"geometritype","Polygon")
                            typen = "polygon"
                        elif (layer.geometryType() == 0):
                            typen = "punkt"
                        elif (layer.geometryType() == 1):
                            typen = "linie"

                        if self.dlg.useSelectedA.isChecked():
                            selection = layer.selectedFeatures()
                            totalantal = layer.selectedFeatureCount()
                            QMessageBox.information(None, "status", "creating DEF for " + str(totalantal) + " selected features")
                        else:
                            selection = layer.getFeatures()
                            totalantal = layer.featureCount()
                            QMessageBox.information(None, "status", "creating DEF for all " + str(totalantal) + " features")

                        defnr = 0
                        nummernu = 0
                        Z=0

                        with open(self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat", "w") as bat_file:
                            bat_file.write("cd " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\n")

                        for feat in selection:

                            geom = feat.geometry()
                            nummernu = nummernu + 1

                            if (typen == "polygon"):
                                Geometri = geom.asPolygon()
                            elif (typen == "punkt"):
                                Geometri = geom.asPoint()
                            else:
                                Geometri = geom.asLine()

                            # ImageID = feat['ImageID']
                            ImageID = feat[self.dlg.ortonamefield.currentText()]

                            if self.dlg.radioButton_fieldpath.isChecked():
                                #text_file.write("IMG= " + str(feat[self.dlg.inField1.currentText()]) + "/" + ImageID + ".tif" + " \n")
                                #text_file.write("IMG= " + str.replace(str.replace(str(feat[self.dlg.inField1.currentText()]),"_JPEG","_TIFF"),".jpg",".tif") + " \n")
                                if ((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg'):
                                    imgpath = + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif"
                                else:
                                    imgpath = str(feat[self.dlg.inField1.currentText()])
                            else:
                                imgpath = os.path.dirname(self.dlg.inDir.text()) + "/" + ImageID + ".tif"



                            # imgpath = os.path.dirname(self.dlg.inDir.text()) + "/" + ImageID + ".tif"
                            RES = self.dlg.lineEditPixelSize.text()
                            OName = "O" + ImageID + ".tif"
                            defName = self.dlg.outDir.text() + "\\" + ImageID + ".def"
                            ortName = self.dlg.lineEdit_workdir.text() + "\\" + OName
                            DEMpath = self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc"

                            geo = feat.geometry()
                            cameraID = feat["cameraid"]
                            imageDate = feat["TimeUTC"]
                            try:
                                coneID = feat["ConeID"]
                            except:
                                coneID = '0'
                            IO = rs.getIO(cameraID, coneID,imageDate)
                            pix = IO[3]
                            dimX = IO[4]*-2/pix
                            dimY = IO[5]*-2/pix

                            filnavn = feat["imageid"]
                            X0 = feat["easting"]
                            Y0 = feat["northing"]
                            Z0 = feat["height"]
                            Ome = feat["omega"]
                            Phi = feat["phi"]
                            Kap = feat["kappa"]


                            EO = [X0, Y0, Z0, Ome, Phi, Kap]

                            # QO footprint
                            if self.dlg.checkBox_bbox.isChecked():
                                #QMessageBox.information(None, "Settings","benytter footprint shp")
                                TLX = int(round((geom.boundingBox().xMinimum() / float(RES)), 0) * float(RES))
                                TLY = int(round((geom.boundingBox().yMaximum() / float(RES)), 0) * float(RES))

                                LRX = int(round((geom.boundingBox().xMaximum() / float(RES)), 0) * float(RES))
                                LRY = int(round((geom.boundingBox().yMinimum() / float(RES)), 0) * float(RES))

                                UL = [TLX, TLY]
                                UR = [LRX,TLY]
                                LR = [LRX,LRY]
                                LL = [TLX,LRY]

                                #UL = rs.ray(IO, EO, Z, 0 , 0)
                                #UR = rs.ray(IO, EO, Z, 0 , dimY)
                                #LR = rs.ray(IO, EO, Z, dimX , dimY)
                                #LL = rs.ray(IO, EO, Z, dimX , 0)
                            else:
                                if (dimX < dimY):
                                    UL = rs.ray(IO, EO, Z, dimX * 0.25, dimY * 0.07)
                                    UR = rs.ray(IO, EO, Z, dimX * 0.25, dimY * 0.93)
                                    LR = rs.ray(IO, EO, Z, dimX * 0.75, dimY * 0.93)
                                    LL = rs.ray(IO, EO, Z, dimX * 0.75, dimY * 0.07)
                                else:
                                    UL = rs.ray(IO, EO, Z, dimX * 0.07, dimY * 0.25)
                                    UR = rs.ray(IO, EO, Z, dimX * 0.07, dimY * 0.75)
                                    LR = rs.ray(IO, EO, Z, dimX * 0.93, dimY * 0.75)
                                    LL = rs.ray(IO, EO, Z, dimX * 0.93, dimY * 0.25)

                            Polyg = [(UL[0], UL[1]), (UR[0], UR[1]), (LR[0], LR[1]), (LL[0], LL[1])]
                            #QMessageBox.information(None, "Settings", str(Polyg))

                            if self.dlg.checkBoxGoGoMinions.isChecked():
                                orto_batfil = basepath + filnavn + '.bat'
                                defName = basepath + filnavn + '.def'

                            else:
                                orto_batfil = self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat"

                            if self.dlg.checkBoxGoGoMinions.isChecked():
                                with open(orto_batfil, "w") as bat_file:
                                    defnr = defnr + 1

                                    # ***  processingmanager info ***
                                    jobnavn = ImageID[5:10]
                                    pdone = int(float(nummernu) / float(totalantal) * 100)
                                    bat_file.write('python C:/temp/writeProgress.py ' + jobnavn + " " + str(pdone) + " \n")

                                    bbox = rs.BoundingBox(Polyg)
                                    TLX = int(round((bbox[0] / float(RES)), 0) * float(RES))
                                    TLY = int(round((bbox[3] / float(RES)), 0) * float(RES))
                                    LRX = int(round((bbox[1] / float(RES)), 0) * float(RES))
                                    LRY = int(round((bbox[2] / float(RES)), 0) * float(RES))
                                    BoBox = QgsGeometry.fromWkt('MULTIPOLYGON (((' + str(TLX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(TLY) + ')))')
                                    bat_file.write("cd c:\\temp \n")
                                    bat_file.write("net use P: /delete\n")
                                    bat_file.write("net use P: \\\\10.48.196.223\\Peta_Lager_3 rs@1809GEOD /user:PROD\\b025527 /persistent:yes\n")
                                    bat_file.write("net use X: /delete\n")
                                    bat_file.write("net use X: \\\\10.48.195.15\\Data_4 rs@1809GEOD /user:PROD\\b025527 /persistent:yes\n")
                                    bat_file.write("net use Y: /delete\n")
                                    bat_file.write("net use Y: \\\\10.48.196.73\\Data_1 rs@1809GEOD /user:PROD\\b025527 /persistent:yes\n")
                                    bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                    bat_file.write("C:\\dev\\COWS\\orto.exe -def " + defName + "\n")
                                    bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                    bat_file.write("REM *** Move Output *** \n")
                                    if self.dlg.checkBoxMinionsOut.isChecked():
                                        bat_file.write("move " + self.dlg.outDir.text() + "\\" + OName + " F:\\JOB\\DATA\\RemoteSensing\\Drift\\GRU\\orto_output \n")
                                    bat_file.write("REM *** CleanUP *** \n")
                                    bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\DTM_" + ImageID + ".*\n")
                                    if self.dlg.checkBoxDelTiff.isChecked():
                                        bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\O" + ImageID + ".*\n")


                            else:
                                with open(orto_batfil, "a") as bat_file:
                                    defnr = defnr + 1

                                    # ***  processingmanager info ***
                                    jobnavn = ImageID[5:10]
                                    pdone = int(float(nummernu) / float(totalantal) * 100)
                                    bat_file.write('python C:/temp/writeProgress.py ' + jobnavn + " " + str(pdone) + " \n")

                                    bbox = rs.BoundingBox(Polyg)
                                    TLX = int(round((bbox[0] / float(RES)), 0) * float(RES))
                                    TLY = int(round((bbox[3] / float(RES)), 0) * float(RES))
                                    LRX = int(round((bbox[1] / float(RES)), 0) * float(RES))
                                    LRY = int(round((bbox[2] / float(RES)), 0) * float(RES))
                                    #BoBox = 'POLYGON (('+ str(TLX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(TLY) + '))'
                                    BoBox =QgsGeometry.fromWkt('MULTIPOLYGON ((('+ str(TLX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(TLY) + ')))')
                                    #QMessageBox.information(None, "bobox",BoBox)

                                    # ***  write BAT file ***
                                    if self.dlg.radioButtonDEM_2007.isChecked():
                                        bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(
                                            LRY - (float(RES) * 20)) + " \\\\c1200038\Data\dtm2007\dtm2007.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                        # bat_file.write("gdal_translate -of AAIGrid -projwin " + str(float(X_0)-(OSizeX/1.8)) + " " + str(float(Y_0)+(OSizeY/1.8)) + " " + str(float(X_0) + (OSizeX/1.8)) + " " + str(float(Y_0) - (OSizeY/1.8)) + " \\\\c1200038\Data\dtm2007\dtm2007.vrt " + self.lineEdit_workdir.text()+"\\DTM_"+ImageID+".asc\n")
                                    elif self.dlg.radioButtonDEM_2015.isChecked():
                                        bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(
                                            LRY - (float(RES) * 20)) + " F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                        # bat_file.write("gdal_translate -of AAIGrid -projwin " + str(float(X_0)-(OSizeX/1.8)) + " " + str(float(Y_0)+(OSizeY/1.8)) + " " + str(float(X_0) + (OSizeX/1.8)) + " " + str(float(Y_0) - (OSizeY/1.8)) + " \\\\Kms.adroot.dk\dhm2007-server\DHM-E\samlet_20150409.vrt " + self.lineEdit_workdir.text()+"\\DTM_"+ImageID+".asc\n")
                                    else:
                                        pass

                                    # create tif file fro processing
                                    if (self.dlg.radioButton_fieldpath.isChecked() and ((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg')):
                                        bat_file.write('gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")

                                    if self.dlg.checkBoxGoGoMinions.isChecked():
                                        bat_file.write("C:\\dev\\COWS\\orto.exe -def " + defName + "\n")
                                    else:
                                        bat_file.write(os.path.dirname(__file__) + "\\orto.exe -def " + self.dlg.outDir.text() + "\\" + ImageID + ".def\n")
                                    bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\DTM_" + ImageID + ".*\n")
                                    bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                    if self.dlg.checkBoxDelTiff.isChecked():
                                        bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\O" + ImageID + ".*\n")




                            # *** write DEF file ***
                            rs.createDef(defName, imgpath, DEMpath, ortName, IO, EO, Polyg, RES)
                            if self.dlg.checkBoxGoGoMinions.isChecked():
                                rs.MinionManager('Orto', orto_batfil, CHKuser, BoBox)

                        if self.dlg.checkBoxCreateVRT.isChecked():
                            with open(self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat", "a") as bat_file:
                                # bat_file.write('ECHO ^<p/^>^<font color="orange"^>^<b^>Procesing: ^</b^>^<font color="black"^>Building VRT ^</p^>>"F:\GEO\DATA\RemoteSensing\Drift\Processing\Status_C1200010.html"\n')
                                # bat_file.write('ftp -i -s:u.ftp\n')
                                bat_file.write("python C:/temp/writeProgress.py Building_VRT 0" + "\n")
                                bat_file.write("gdalbuildvrt " + self.dlg.outDir.text() + "\\" + self.dlg.inShapeA.currentText() + ".vrt " + self.dlg.outDir.text() + "\\*.tif" + "\n")

                                # bat_file.write('ECHO ^<p/^>^<font color="orange"^>^<b^>Procesing: ^</b^>^<font color="black"^>Adding Overlays ^</p^>>"F:\GEO\DATA\RemoteSensing\Drift\Processing\Status_C1200010.html"\n')
                                # bat_file.write('ftp -i -s:u.ftp\n')
                                bat_file.write("python C:/temp/writeProgress.py Adding_Overlay 0" + "\n")
                                bat_file.write(
                                    "gdaladdo " + self.dlg.outDir.text() + "\\" + self.dlg.inShapeA.currentText() + ".vrt " + " -r average -ro --config GDAL_CACHEMAX 900 --config COMPRESS_OVERVIEW JPEG --config JPEG_QUALITY_OVERVIEW 85 --config PHOTOMETRIC_OVERVIEW YCBCR --config INTERLEAVE_OVERVIEW PIXEL --config BIGTIFF_OVERVIEW YES 2 4 10 25 50 100 200 500 1000" + "\n")

                                # bat_file.write('ECHO ^<p/^>^<font color="green"^>^<b^>Procesing: ^</b^>^<font color="black"^>Procesing complete ^</b^>^<font color="black"^>^</p^>>"F:\GEO\DATA\RemoteSensing\Drift\Processing\Status_C1200010.html"\n')
                                # bat_file.write('ftp -i -s:u.ftp\n')
                                bat_file.write("python C:/temp/writeProgress.py Processing_Done 101" + "\n")

                                if self.dlg.checkBoxDelTiff.isChecked():
                                    pass
                                else:
                                    bat_file.write(
                                        "gdalbuildvrt -srcnodata \"0 0 0\" " + self.dlg.outDir.text() + ".vrt " + self.dlg.outDir.text() + "\\*.tif" + "\n")

                        if self.dlg.checkBoxGoGoMinions.isChecked():
                            QMessageBox.information(None, "Status", "Ortho photo def-files have been added to GRU's jobque. \n\n You can follow the progress on Skynet.")
                        else:
                            QMessageBox.information(None, "Status","DEF and Batfile created. \n\nPlease run " + self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat from a OSGEO4W shell")

                pass

    def runOLD(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()

        QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.checkA)
        QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.update1)
        QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.update_ortonamefield)
        self.dlg.setWindowTitle(self.tr("Make Ortho"))
        # populate layer list
        self.dlg.progressBar.setValue(0)
        # mapCanvas = self.iface.mapCanvas()
        # layers = ftools_utils.getLayerNames([QGis.Point, QGis.Line, QGis.Polygon])
        # self.dlg.inShapeA.addItems(layers)

        mapCanvas = self.iface.mapCanvas()
        lyrs = self.iface.legendInterface().layers()
        lyr_list = []
        for layer in lyrs:
            lyr_list.append(layer.name())
        self.dlg.inShapeA.clear()
        self.dlg.inShapeA.addItems(lyr_list)

        self.dlg.progressBar.hide()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            import subprocess
            import psycopg2

            conn = psycopg2.connect(
                "dbname={name} user={user} host={host} password={pswd} port={port}".format(
                    name=self.settings.value('database'),
                    user=self.settings.value('username'),
                    schem=self.settings.value('schema'),
                    tabl=self.settings.value('table'),
                    host=self.settings.value('hostname'),
                    pswd=self.settings.value('password'),
                    port=self.settings.value('port'),
                )
            )

            cur = conn.cursor()

            inputFilNavn = self.dlg.inShapeA.currentText()

            canvas = self.iface.mapCanvas()
            allLayers = canvas.layers()

            for i in allLayers:
                # QMessageBox.information(None, "test input", i.name())
                if (i.name() == inputFilNavn):
                    layer = i

                    # QMessageBox.information(None, "type", str(layer.geometryType()))
                    if (layer.geometryType() == 2):
                        # QMessageBox.information(None,"geometritype","Polygon")
                        typen = "polygon"
                    elif (layer.geometryType() == 0):
                        typen = "punkt"
                    elif (layer.geometryType() == 1):
                        typen = "linie"

                    if self.dlg.useSelectedA.isChecked():
                        selection = layer.selectedFeatures()
                        totalantal = layer.selectedFeatureCount()
                        QMessageBox.information(None, "status", "creating DEF for "+ str(totalantal) + " selected features")
                    else:
                        selection = layer.getFeatures()
                        totalantal = layer.featureCount()
                        QMessageBox.information(None, "status", "creating DEF for all "+ str(totalantal) + " features")

                    defnr = 0

                    nummernu = 0

                    with open(self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat","w") as bat_file:
                        bat_file.write("cd " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\n")

                    for feat in selection:

                        geom = feat.geometry()
                        nummernu = nummernu + 1


                        if (typen == "polygon"):
                            Geometri = geom.asPolygon()
                        elif (typen == "punkt"):
                            Geometri = geom.asPoint()
                        else:
                            Geometri = geom.asLine()

                        #ImageID = feat['ImageID']
                        ImageID = feat[self.dlg.ortonamefield.currentText()]

                        # load Camera calibration
                        CameraID = feat['CameraID']
                        try:
                            ConeID = feat['coneid']
                            #QMessageBox.information(None,'ConeID',ConeID)
                        except (RuntimeError, TypeError, NameError, KeyError):
                            ConeID = '0'
                            #QMessageBox.information(None, 'ConeID',ConeID)
                        #QMessageBox.information(None, 'status', 'kobler paa DB med '+'SELECT * FROM camera_calibrations WHERE camera_id = \'' + str(CameraID) + '\' and cone_id = \'' + ConeID +'\' order by calibration_date DESC limit 1')
                        #dbkald = "SELECT * FROM remote_sensing.camera_calibrations WHERE camera_id = \'" + str(CameraID) + "\' and cone_id = \'" + ConeID +"\' order by calibration_date DESC limit 1"
                        dbkald = "SELECT * FROM remote_sensing.camera_calibrations WHERE camera_id = \'" + str(CameraID) + "\' and cone_id = \'" + ConeID + "\' order by calibration_date DESC limit 1"
                        cur.execute(dbkald)
                        ccdb_svar = cur.fetchone()
                        # QMessageBox.information(None, "db info", str(ccdb_svar))
                        try:
                            imgRot = ccdb_svar[14]
                            CamRot = ccdb_svar[13]
                            CC = float(ccdb_svar[1]) * (-1)  # 100.5
                            pix = ccdb_svar[2] / 1000  # 0.006
                            SensorX = ccdb_svar[5]  # 11310
                            SensorY = ccdb_svar[6]  # 17310
                            PriXin = float(ccdb_svar[3])  # (-18)
                            PriYin = float(ccdb_svar[4])  # (0)
                            coneid = ccdb_svar[15]
                        except (RuntimeError, TypeError, NameError, ValueError):
                            QMessageBox.information(None, "General Error","Camera calibration for " + str(CameraID) + " not found in DB!")
                            noError = False
                            return

                        # Read fields

                        OName = "O" + ImageID + ".tif"
                        #QMessageBox.information(None, "navn til orto",OName)
                        RES = self.dlg.lineEditPixelSize.text()
                        if CamRot == 0:
                            IL1 = " 0.000 " + str(pix)
                            IL2 = str(pix) + " 0.000 "
                            IL3 = str(SensorX) + " " + str(SensorY)  # -33.9300000 51.930000000"
                            PriY = PriXin
                            PriX = PriYin

                        elif CamRot == 270:
                            IL1 = str(pix) + " 0.000"
                            IL2 = "0.000 " + str(pix * (-1))
                            IL3 = str(SensorX) + " " + str(SensorY * (-1))
                            PriY = PriYin
                            PriX = PriXin

                        elif CamRot == 90:
                            IL1 = str(pix) + " 0.000"
                            IL2 = "0.000 " + str(pix * (-1))
                            IL3 = str(SensorY) + " " + str(SensorX * (-1))
                            PriY = PriYin
                            PriX = PriXin

                        elif CamRot == 180:
                            IL1 = " 0.000 " + str(pix)
                            IL2 = str(pix) + " 0.000 "
                            IL3 = str(SensorY) + " " + str(SensorX * (-1))
                            PriY = PriXin
                            PriX = PriYin

                        elif CamRot == 999:
                            IL1 = str(pix) + " 0.000"
                            IL2 = "0.000 " + str(pix * (-1))
                            IL3 = str(SensorY) + " " + str(SensorX * (-1))
                            PriY = PriYin
                            PriX = PriXin
                        else:
                            QMessageBox.warning(None, "Camera Fail", "Illigal Camera Rotation" + str(CamRot))
                            exit()

                        X_0 = str(feat['Easting'])
                        Y_0 = str(feat['Northing'])
                        Z_0 = str(feat['Height'])
                        OME = str(feat['Omega'])
                        PHI = str(feat['Phi'])
                        KAP = str(feat['Kappa'])

                        # if self.checkBox_bbox.isChecked():
                        if typen == "polygon":

                            TLX = int(round((geom.boundingBox().xMinimum() / float(RES)), 0) * float(RES))
                            TLY = int(round((geom.boundingBox().yMaximum() / float(RES)), 0) * float(RES))

                            LRX = int(round((geom.boundingBox().xMaximum() / float(RES)), 0) * float(RES))
                            LRY = int(round((geom.boundingBox().yMinimum() / float(RES)), 0) * float(RES))

                            OSizeX = (LRX - TLX)
                            OSizeY = (TLY - LRY)
                            # QMessageBox.information(None, "db info", str(OSizeX))

                            SZX = (LRX - TLX) / float(RES)
                            SZY = (TLY - LRY) / float(RES)

                        else:
                            usersetangle = float(self.dlg.lineEditImageAngle.text())
                            clipKAM = float(KAP) - float(CamRot) + float(imgRot)

                            if (pix == 0.006):
                                if (clipKAM > -630 - usersetangle and clipKAM < -630 + usersetangle) or (
                                        clipKAM > -450 - usersetangle and clipKAM < -450 + usersetangle) or (
                                        clipKAM > -270 - usersetangle and clipKAM < -270 + usersetangle) or (
                                        clipKAM > -90 - usersetangle and clipKAM < -90 + usersetangle) or (
                                        clipKAM > 90 - usersetangle and clipKAM < 90 + usersetangle) or (
                                        clipKAM > 270 - usersetangle and clipKAM < 270 + usersetangle):
                                    OSizeX = 2200
                                    OSizeY = 800
                                elif (clipKAM > -720 - usersetangle and clipKAM < -720 + usersetangle) or (
                                        clipKAM > -540 - usersetangle and clipKAM < -540 + usersetangle) or (
                                        clipKAM > -360 - usersetangle and clipKAM < -360 + usersetangle) or (
                                        clipKAM > -180 - usersetangle and clipKAM < -180 + usersetangle) or (
                                        clipKAM > 0 - usersetangle and clipKAM < 0 + usersetangle) or (
                                        clipKAM > 180 - usersetangle and clipKAM < 180 + usersetangle):
                                    OSizeX = 800
                                    OSizeY = 2200
                                else:
                                    OSizeX = 2200
                                    OSizeY = 2200
                            elif (pix == 0.0052):
                                if (clipKAM > -630 - usersetangle and clipKAM < -630 + usersetangle) or (
                                        clipKAM > -450 - usersetangle and clipKAM < -450 + usersetangle) or (
                                        clipKAM > -270 - usersetangle and clipKAM < -270 + usersetangle) or (
                                        clipKAM > -90 - usersetangle and clipKAM < -90 + usersetangle) or (
                                        clipKAM > 90 - usersetangle and clipKAM < 90 + usersetangle) or (
                                        clipKAM > 270 - usersetangle and clipKAM < 270 + usersetangle):
                                    OSizeX = int(float(Z_0) * 0.90)  # 3200
                                    OSizeY = int(float(Z_0) * 0.30)  # 1000
                                    #OSizeX = 2500
                                    #OSizeY = 900
                                elif (clipKAM > -720 - usersetangle and clipKAM < -720 + usersetangle) or (
                                        clipKAM > -540 - usersetangle and clipKAM < -540 + usersetangle) or (
                                        clipKAM > -360 - usersetangle and clipKAM < -360 + usersetangle) or (
                                        clipKAM > -180 - usersetangle and clipKAM < -180 + usersetangle) or (
                                        clipKAM > 0 - usersetangle and clipKAM < 0 + usersetangle) or (
                                        clipKAM > 180 - usersetangle and clipKAM < 180 + usersetangle):
                                    OSizeX = int(float(Z_0) * 0.30)  # 3200
                                    OSizeY = int(float(Z_0) * 0.90)  # 1000
                                    #OSizeX = 900
                                    #OSizeY = 2500
                                else:
                                    OSizeX = int(float(Z_0) * 0.90)  # 3200
                                    OSizeY = int(float(Z_0) * 0.90)  # 1000
                                    #OSizeX = 2500
                                    #OSizeY = 2500
                            elif (pix == 0.0046):
                                if (clipKAM > -630 - usersetangle and clipKAM < -630 + usersetangle) or (
                                        clipKAM > -450 - usersetangle and clipKAM < -450 + usersetangle) or (
                                        clipKAM > -270 - usersetangle and clipKAM < -270 + usersetangle) or (
                                        clipKAM > -90 - usersetangle and clipKAM < -90 + usersetangle) or (
                                        clipKAM > 90 - usersetangle and clipKAM < 90 + usersetangle) or (
                                        clipKAM > 270 - usersetangle and clipKAM < 270 + usersetangle):
                                    OSizeX = int(float(Z_0)*0.95) #3200
                                    OSizeY = int(float(Z_0)*0.33) #1000
                                elif (clipKAM > -720 - usersetangle and clipKAM < -720 + usersetangle) or (
                                        clipKAM > -540 - usersetangle and clipKAM < -540 + usersetangle) or (
                                        clipKAM > -360 - usersetangle and clipKAM < -360 + usersetangle) or (
                                        clipKAM > -180 - usersetangle and clipKAM < -180 + usersetangle) or (
                                        clipKAM > 0 - usersetangle and clipKAM < 0 + usersetangle) or (
                                        clipKAM > 180 - usersetangle and clipKAM < 180 + usersetangle):
                                    OSizeX = int(float(Z_0) * 0.33)  # 1000
                                    OSizeY = int(float(Z_0) * 0.95)  # 2800
                                else:
                                    OSizeX = int(float(Z_0)*0.95) #3200
                                    OSizeY = int(float(Z_0)*0.95) #3200
                            elif (pix == 0.0039):
                                if (clipKAM > -630 - usersetangle and clipKAM < -630 + usersetangle) or (
                                        clipKAM > -450 - usersetangle and clipKAM < -450 + usersetangle) or (
                                        clipKAM > -270 - usersetangle and clipKAM < -270 + usersetangle) or (
                                        clipKAM > -90 - usersetangle and clipKAM < -90 + usersetangle) or (
                                        clipKAM > 90 - usersetangle and clipKAM < 90 + usersetangle) or (
                                        clipKAM > 270 - usersetangle and clipKAM < 270 + usersetangle):
                                    OSizeX = int(float(Z_0)*0.9) #3200
                                    OSizeY = int(float(Z_0)*0.26) #1000
                                elif (clipKAM > -720 - usersetangle and clipKAM < -720 + usersetangle) or (
                                        clipKAM > -540 - usersetangle and clipKAM < -540 + usersetangle) or (
                                        clipKAM > -360 - usersetangle and clipKAM < -360 + usersetangle) or (
                                        clipKAM > -180 - usersetangle and clipKAM < -180 + usersetangle) or (
                                        clipKAM > 0 - usersetangle and clipKAM < 0 + usersetangle) or (
                                        clipKAM > 180 - usersetangle and clipKAM < 180 + usersetangle):
                                    OSizeX = int(float(Z_0)*0.26) #1000
                                    OSizeY = int(float(Z_0)*0.9) #3200)
                                else:
                                    OSizeX = int(float(Z_0)*0.9) #3200
                                    OSizeY = int(float(Z_0)*0.9) #3200

                            TLX = float(X_0) - (OSizeX / 2)
                            TLY = float(Y_0) + (OSizeY / 2)
                            LRX = float(X_0) + (OSizeX / 2)
                            LRY = float(Y_0) - (OSizeY / 2)

                            SZX = OSizeX / float(RES)
                            SZY = OSizeY / float(RES)




                        with open(self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat", "a") as bat_file:
                            defnr = defnr + 1

                            # ***  processingmanager info ***
                            jobnavn = ImageID[5:10]
                            pdone = int(float(nummernu)/float(totalantal)*100)
                            bat_file.write('python C:/temp/writeProgress.py ' + jobnavn + " " + str(pdone) + " \n")

                            # ***  write BAT file ***
                            if self.dlg.radioButtonDEM_2007.isChecked():
                                bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " \\\\c1200038\Data\dtm2007\dtm2007.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                # bat_file.write("gdal_translate -of AAIGrid -projwin " + str(float(X_0)-(OSizeX/1.8)) + " " + str(float(Y_0)+(OSizeY/1.8)) + " " + str(float(X_0) + (OSizeX/1.8)) + " " + str(float(Y_0) - (OSizeY/1.8)) + " \\\\c1200038\Data\dtm2007\dtm2007.vrt " + self.lineEdit_workdir.text()+"\\DTM_"+ImageID+".asc\n")
                            elif self.dlg.radioButtonDEM_2015.isChecked():
                                bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                # bat_file.write("gdal_translate -of AAIGrid -projwin " + str(float(X_0)-(OSizeX/1.8)) + " " + str(float(Y_0)+(OSizeY/1.8)) + " " + str(float(X_0) + (OSizeX/1.8)) + " " + str(float(Y_0) - (OSizeY/1.8)) + " \\\\Kms.adroot.dk\dhm2007-server\DHM-E\samlet_20150409.vrt " + self.lineEdit_workdir.text()+"\\DTM_"+ImageID+".asc\n")
                            else:
                                pass

                            # create tif file fro processing
                            # QMessageBox.information(None, "db info", (os.path.splitext(IMG)[1]).lower())

                            if (self.dlg.radioButton_fieldpath.isChecked() and ((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg')):
                                bat_file.write('gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")

                            bat_file.write(os.path.dirname(__file__) + "\\orto.exe -def " + self.dlg.outDir.text() + "\\" + ImageID + ".def\n")
                            bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/','\\') + "\\DTM_" + ImageID + ".*\n")
                            bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                            if self.dlg.checkBoxDelTiff.isChecked():
                                bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/','\\') + "\\O" + ImageID + ".*\n")

                        # *** write DEF file ***
                        with open(self.dlg.outDir.text() + "\\" + ImageID + ".def", "w") as text_file:
                            text_file.write("PRJ= nill.apr" + " \n")
                            text_file.write("ORI= nill.txt" + " \n")
                            text_file.write("RUN= 0" + " \n")
                            text_file.write("DEL= NO" + " \n")
                            if self.dlg.radioButton_fieldpath.isChecked():
                                #text_file.write("IMG= " + str(feat[self.dlg.inField1.currentText()]) + "/" + ImageID + ".tif" + " \n")
                                #text_file.write("IMG= " + str.replace(str.replace(str(feat[self.dlg.inField1.currentText()]),"_JPEG","_TIFF"),".jpg",".tif") + " \n")
                                if ((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg'):
                                    text_file.write("IMG= "+ self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                else:
                                    text_file.write("IMG= " + str(feat[self.dlg.inField1.currentText()]) + " \n")
                            else:
                                text_file.write("IMG= " + os.path.dirname(self.dlg.inDir.text()) + "/" + ImageID + ".tif" + " \n")
                            if self.dlg.radioButtonDEM_spec.isChecked():
                                text_file.write("DGL= " + self.dlg.lineEditDEM.text() + " \n")
                                text_file.write("DGP= DTM_" + " \n")
                                text_file.write("DGS= 1" + " \n")
                            else:
                                text_file.write("DTM= " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc" + " \n")
                            text_file.write("ORT= " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " \n")
                            text_file.write("TLX= " + str(TLX) + " \n")
                            text_file.write("TLY= " + str(TLY) + " \n")
                            text_file.write("RES= " + RES + " \n")
                            text_file.write("SZX= " + str(math.trunc(SZX)) + " \n")
                            text_file.write("SZY= " + str(math.trunc(SZY)) + " \n")
                            text_file.write("R34= NO" + " \n")
                            text_file.write("INT= CUB -1" + " \n")
                            text_file.write("CON= " + str(CC / 1000) + " \n")  # 0.1005
                            text_file.write("XDH= " + str(PriX) + " \n")  # -0.18
                            text_file.write("YDH= " + str(PriY) + " \n")
                            text_file.write("IL1= " + IL1 + " \n")
                            text_file.write("IL2= " + IL2 + " \n")
                            text_file.write("IL3= " + IL3 + " \n")
                            text_file.write("X_0= " + X_0 + " \n")
                            text_file.write("Y_0= " + Y_0 + " \n")
                            text_file.write("Z_0= " + Z_0 + " \n")
                            text_file.write("DRG= DEG" + " \n")
                            text_file.write("OME= " + OME + " \n")
                            text_file.write("PHI= " + PHI + " \n")
                            text_file.write("KAP= " + KAP + " \n")
                            text_file.write("MBF= 870" + " \n")
                            text_file.write("BBF= 999999" + " \n")
                            text_file.write("STR= NO" + " \n")

                            if typen == "polygon" and self.dlg.checkBox_bbox.isChecked():
                                for punktliste in Geometri:
                                    text_file.write("BPL= " + str(len(punktliste)) + " 0" + " \n")
                                    punktnummer = 0
                                    for punkt in punktliste:
                                        punktnummer = punktnummer + 1
                                        text_file.write("BP" + str(punktnummer) + "=" + str(punkt.x()) + " " + str(punkt.y()) + " \n")

                            text_file.close()

                    with open(self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat","a") as bat_file:
                        #bat_file.write('ECHO ^<p/^>^<font color="orange"^>^<b^>Procesing: ^</b^>^<font color="black"^>Building VRT ^</p^>>"F:\GEO\DATA\RemoteSensing\Drift\Processing\Status_C1200010.html"\n')
                        #bat_file.write('ftp -i -s:u.ftp\n')
                        bat_file.write("python C:/temp/writeProgress.py Building_VRT 0"+ "\n")
                        bat_file.write("gdalbuildvrt " + self.dlg.outDir.text() + "\\" + self.dlg.inShapeA.currentText() + ".vrt " + self.dlg.outDir.text() + "\\*.tif" + "\n")

                        #bat_file.write('ECHO ^<p/^>^<font color="orange"^>^<b^>Procesing: ^</b^>^<font color="black"^>Adding Overlays ^</p^>>"F:\GEO\DATA\RemoteSensing\Drift\Processing\Status_C1200010.html"\n')
                        #bat_file.write('ftp -i -s:u.ftp\n')
                        bat_file.write("python C:/temp/writeProgress.py Adding_Overlay 0"+ "\n")
                        bat_file.write("gdaladdo " + self.dlg.outDir.text() + "\\" + self.dlg.inShapeA.currentText() + ".vrt " + " -r average -ro --config GDAL_CACHEMAX 900 --config COMPRESS_OVERVIEW JPEG --config JPEG_QUALITY_OVERVIEW 85 --config PHOTOMETRIC_OVERVIEW YCBCR --config INTERLEAVE_OVERVIEW PIXEL --config BIGTIFF_OVERVIEW YES 2 4 10 25 50 100 200 500 1000" + "\n")

                        #bat_file.write('ECHO ^<p/^>^<font color="green"^>^<b^>Procesing: ^</b^>^<font color="black"^>Procesing complete ^</b^>^<font color="black"^>^</p^>>"F:\GEO\DATA\RemoteSensing\Drift\Processing\Status_C1200010.html"\n')
                        #bat_file.write('ftp -i -s:u.ftp\n')
                        bat_file.write("python C:/temp/writeProgress.py Processing_Done 101"+ "\n")

                        if self.dlg.checkBoxDelTiff.isChecked():
                            pass
                        else:
                            bat_file.write(
                                "gdalbuildvrt -srcnodata \"0 0 0\" " + self.dlg.outDir.text() + ".vrt " + self.dlg.outDir.text() + "\\*.tif" + "\n")

                    QMessageBox.information(None, "Settings",
                                            "DEF and Batfile created. \n\nPlease run " + self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat from a OSGEO4W shell")

            conn.close()
            pass

    def build_filelist(self):
        self.fdl.show()

        # layers = ftools_utils.getLayerNames([QGis.Point, QGis.Line, QGis.Polygon])
        # self.fdl.inShapeImg.addItems(layers)
        # self.fdl.inShapeTiles.addItems(layers)

        mapCanvas = self.iface.mapCanvas()
        lyrs = self.iface.legendInterface().layers()
        lyr_list = []
        for layer in lyrs:
            lyr_list.append(layer.name())
        self.fdl.inShapeImg.clear()
        self.fdl.inShapeImg.addItems(lyr_list)
        self.fdl.inShapeTiles.clear()
        self.fdl.inShapeTiles.addItems(lyr_list)

        # Run the dialog event loop
        result = self.fdl.exec_()
        # See if OK was pressed
        if result:

            lyriPoly = self.fdl.inShapeTiles.currentText()
            lyriPnts = self.fdl.inShapeImg.currentText()
            outSti = self.fdl.outDir.text()

            # QMessageBox.information(None, "fusk", lyriPoly + "\n" + lyriPnts + "\n" + outSti)

            canvas = self.iface.mapCanvas()
            allLayers = canvas.layers()

            for i in allLayers:
                # QMessageBox.information(None, "test input", i.name())
                if (i.name() == lyriPoly):
                    if (i.geometryType() == 2):
                        lyrPoly = i
                    else:
                        QMessageBox.information(None, "Mosaic file error", lyriPoly + " is not a polygon. Exiting!")
                        pass
                if (i.name() == lyriPnts):
                    if (i.geometryType() == 0) or (i.geometryType() == 1) or (i.geometryType() == 2):
                        lyrPnts = i
                    else:
                        QMessageBox.information(None, "Image name file error",
                                                lyriPnts + " is not vector data. Exiting!")
                        pass

            featsPoly = lyrPoly.selectedFeatures()
            # lyrPnts = lyrPnts.selectedFeatures()


            for featPoly in featsPoly:
                zipPoly = featPoly["kn10kmdk"]
                geomPoly = featPoly.geometry()

                # featsPnt = lyrPnts.selectedFeatures().getFeatures(QgsFeatureRequest().setFilterRect(geomPoly.boundingBox().buffer(1200)))
                featsPnt = lyrPnts.selectedFeatures()

                # QMessageBox.information(None, "fusk", zipPoly)

                with open(outSti + "/" + zipPoly + ".filelist", "w") as text_file:
                    for featPnt in featsPnt:
                        if featPnt.geometry().within(geomPoly.buffer(1400, 3)):
                            text_file.write('O' + featPnt["imageid"] + '.tif\n')
                text_file.close()

        QMessageBox.information(None, "File list writer", "Done!")

        pass

