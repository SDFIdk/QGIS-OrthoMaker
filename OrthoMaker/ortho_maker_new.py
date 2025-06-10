# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OrthoMaker
                                 A QGIS plugin
 Pluginn to calculate orthophotos from images and a DEM
                              -------------------
        begin                : 2022-05-06
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Andrew Flatman / Danish Mapping Agency
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import getpass
import socket
import sys
import math
#import .remote_sensing # as rs
from .remote_sensing import remote_sensing as rs


# Initialize Qt resources from file resources.py
from .resources import * 
# Import the code for the dialog
from .ortho_maker_dialog import OrthoMakerDialog
import os.path


class OrthoMaker:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
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
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Ortho Maker')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
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
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/ortho_maker/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create Ortho Photos'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Ortho Maker'),
                action)
            self.iface.removeToolBarIcon(action)


    def runold(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = OrthoMakerDialog()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def update_ortonamefield(self, inputLayer):
        self.dlg.ortonamefield.clear()
        changedLayer = ftools_utils.getVectorLayerByName(unicode(inputLayer))
        changedField = ftools_utils.getFieldList(changedLayer)
        for f in changedField:
            if f.type() == QVariant.Int or f.type() == QVariant.String:
                self.dlg.ortonamefield.addItem(unicode(f.name()))

    
    
    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = OrthoMakerDialog()

        # show the dialog
        self.dlg.show()

        CHKuser = getpass.getuser()
        maskinenavn = (socket.gethostname())
        basepath = 'F:\\JOB\\DATA\\RemoteSensing\\Drift\\GRU\\orto_bat_files\\'

        #QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.checkA)
        #QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.update1)
        #QObject.connect(self.dlg.inShapeA, SIGNAL("currentIndexChanged(QString)"), self.update_ortonamefield)
        #self.dlg.setWindowTitle(self.tr("Make Ortho"))
        ## populate layer list
        #self.dlg.progressBar.setValue(0)
        #mapCanvas = self.iface.mapCanvas()
        #lyrs = self.iface.legendInterface().layers()
        #lyr_list = []
        #for layer in lyrs:
        #    lyr_list.append(layer.name())
        #self.dlg.inShapeA.clear()
        #self.dlg.inShapeA.addItems(lyr_list)

        #self.dlg.progressBar.hide()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # See if OK was pressed
            if result:
                print ("yay")

                inputFilNavn = self.dlg.inShapeA.currentText()
                canvas = self.iface.mapCanvas()
                allLayers = canvas.layers()
                print (inputFilNavn)
                print (allLayers)

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
                            print ("creating DEF for " + str(totalantal) + " selected features")
                        else:
                            selection = layer.getFeatures()
                            totalantal = layer.featureCount()
                            QMessageBox.information(None, "status", "creating DEF for all " + str(totalantal) + " features")
                            print ("creating DEF for all " + str(totalantal) + " features")

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

                            #ImageID = feat['imageid']
                            ImageID = feat[self.dlg.ortonamefield.currentText()]

                            if self.dlg.radioButton_fieldpath.isChecked():
                                #text_file.write("IMG= " + str(feat[self.dlg.inField1.currentText()]) + "/" + ImageID + ".tif" + " \n")
                                #text_file.write("IMG= " + str.replace(str.replace(str(feat[self.dlg.inField1.currentText()]),"_JPEG","_TIFF"),".jpg",".tif") + " \n")
                                print (ImageID)
                                print(self.dlg.lineEdit_workdir.text())
                                
                                ##fix jpegs
                                #if ((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg'):
                                #    imgpath = str(self.dlg.lineEdit_workdir.text()) + "\\DTM_" + ImageID + ".tif"
                                #else:
                                #    imgpath = str(feat[self.dlg.inField1.currentText()])

                                #always fix jpegs, also in tiffjpegs
                                imgpath = str(self.dlg.lineEdit_workdir.text()) + "\\DTM_" + ImageID + ".tif"

                            else:
                                imgpath = os.path.dirname(self.dlg.inDir.text()) + "/" + ImageID + ".tif"



                            # imgpath = os.path.dirname(self.dlg.inDir.text()) + "/" + ImageID + ".tif"
                            RES = self.dlg.lineEditPixelSize.text()
                            OName = "O" + ImageID + ".tif"
                            defName = self.dlg.outDir.text() + "\\" + ImageID + ".def"
                            ortName = self.dlg.lineEdit_workdir.text() + "\\" + OName
                            DEMpath = self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc"

                            geo = feat.geometry()
                            cameraID = str(feat["cameraid"])
                            imageDate = str(feat["timeutc"])
                            try:
                                coneID = str(feat["coneid"])
                                print('Eroor#1: ' + coneID)
                                if (coneID == 'NULL'):
                                    coneID =""
                            except:
                                #Fusk/
                                a=1
                                #coneID = '0'
                                #/Fusk
                            print (cameraID +' ' + coneID + ' ' + imageDate)
                            
                            try:
                                CamRot = 270
                                c = feat["focal_length"] * (-1)  # 100.5
                                pix = feat["pixel_size"]/1000 # 0.006
                                dimXi = (feat["image_format_x"]*pix/2)*-1 # -34.008
                                dimYi = (feat["image_format_y"]*pix/2)*-1 # -52.026
                                xx0i = feat["x_ppa"] # (-18)
                                yy0i = feat["y_ppa"] # (0)

                                dimX = dimXi
                                dimY = dimYi
                                xx0 = xx0i
                                yy0 = yy0i

                                IO = [xx0,yy0,c,pix,dimX,dimY,CamRot]
                                inner_ori_table = True
                            except:
                                IO = rs.getIO(cameraID, coneID,imageDate)
                                inner_ori_table = False
                            
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
                            #QMessageBox.information(None, "status", f"EO is {EO}\nIO is {IO}")
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
                            elif self.dlg.checkBoxML.isChecked():
                                if (dimX < dimY):
                                    UL = rs.ray(IO, EO, Z, dimX * 0.07, dimY * 0.07)
                                    UR = rs.ray(IO, EO, Z, dimX * 0.07, dimY * 0.93)
                                    LR = rs.ray(IO, EO, Z, dimX * 0.93, dimY * 0.93)
                                    LL = rs.ray(IO, EO, Z, dimX * 0.93, dimY * 0.07)
                                else:
                                    UL = rs.ray(IO, EO, Z, dimX * 0.07, dimY * 0.07)
                                    UR = rs.ray(IO, EO, Z, dimX * 0.07, dimY * 0.93)
                                    LR = rs.ray(IO, EO, Z, dimX * 0.93, dimY * 0.93)
                                    LL = rs.ray(IO, EO, Z, dimX * 0.93, dimY * 0.07)

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

                            if self.dlg.checkBoxML.isChecked():
                                tres = float(RES)
                                minX = math.trunc(UL[0])
                                maxX = math.trunc(LR[0])
                                maxY = math.trunc(UL[1])
                                minY = math.trunc(LR[1])

                                #NmaxX = minX + ((math.trunc(((maxX-minX)/tres)/1250))*1250*tres)
                                #NminY = maxY - ((math.trunc(((maxY-minY)/tres)/1250))*1250*tres)

                                NmaxX = minX + ((math.trunc(((maxX-minX)/tres)/1000))*1000*tres)
                                NminY = maxY - ((math.trunc(((maxY-minY)/tres)/1000))*1000*tres)

                                Polyg = [(minX, maxY), (NmaxX, maxY), (NmaxX, NminY), (minX, NminY)]

                            else:
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
                                    print(bbox)
                                    TLX = int(round((bbox[0] / float(RES)), 0) * float(RES))
                                    TLY = int(round((bbox[3] / float(RES)), 0) * float(RES))
                                    LRX = int(round((bbox[1] / float(RES)), 0) * float(RES))
                                    LRY = int(round((bbox[2] / float(RES)), 0) * float(RES))
                                    BoBox = QgsGeometry.fromWkt('MULTIPOLYGON (((' + str(TLX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(TLY) + ')))')
                                    bat_file.write("cd c:\\temp \n")
                                    # bat_file.write("net use P: /delete\n")
                                    # bat_file.write("net use P: \\\\10.48.196.223\\Peta_Lager_3 rs@1809GEOD /user:PROD\\b025527 /persistent:yes\n")
                                    # bat_file.write("net use X: /delete\n")
                                    # bat_file.write("net use X: \\\\10.48.195.15\\Data_4 rs@1809GEOD /user:PROD\\b025527 /persistent:yes\n")
                                    # bat_file.write("net use Y: /delete\n")
                                    # bat_file.write("net use Y: \\\\10.48.196.73\\Data_1 rs@1809GEOD /user:PROD\\b025527 /persistent:yes\n")
                                    if self.dlg.radioButtonDEM_2007.isChecked():
                                        bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                    elif self.dlg.radioButtonDEM_spec.isChecked():
                                        if self.dlg.checkBoxGoGoMinions.isChecked():
                                            #bat_file.write('ogr2ogr -f ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=C1507145 port=5432 user= python_script_sdfe  password= python_script_sdfe  dbname= grundkort\" -sql \"select ST_Difference (ST_Union(st_buffer(geom, 40)), ST_Union(st_buffer(geom,-1))) from geodk.bygning WHERE ST_Intersects(geom, \'SRID=25832;POLYGON((' + minX + ' ' + minY + ',' + minX + ' ' + maxY + ',' + maxX + ' ' + maxY + ',' + maxX + ' ' + minY + ',' + minX + ' ' + minY + '))\')\"\n')
                                            bat_file.write('ogr2ogr -f \"ESRI Shapefile\" ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=10.34.133.93 port=5432 user=postgres  password=postgres  dbname= dhmqc\" -sql \"select ST_Difference (ST_Union(st_buffer(wkb_geometry, 40)), ST_Union(st_buffer(wkb_geometry,-1))) from geodk.bygning WHERE ST_Intersects(wkb_geometry, \'SRID=25832;POLYGON((' + minX + ' ' + minY + ',' + minX + ' ' + maxY + ',' + maxX + ' ' + maxY + ',' + maxX + ' ' + minY + ',' + minX + ' ' + minY + '))\')\"\n')
                                            bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:/GDB/DHM/AnvendelseGIS/DSM_20230816.vrt " + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".asc\n")
                                            bat_file.write('gdal_rasterize -burn -9999 -l maske ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".asc\n")
                                            bat_file.write('gdal_translate -a_nodata -9999 ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".asc " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + "m.asc\n")
                                            #bat_file.write('call  C:/OSGeo4W64/bin/gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                            bat_file.write('call  gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + "m.asc " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")                                           
                                        else:
                                            #non rooftop #bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " " + self.dlg.lineEditDEM.text() + " " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                            #bat_file.write('ogr2ogr -f \"ESRI Shapefile\" ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=C1507145 port=5432 user= python_script_sdfe  password= python_script_sdfe  dbname= grundkort\" -sql \"select ST_Difference (ST_Union(st_buffer(geom, 40)), ST_Union(st_buffer(geom,-1))) from geodk.bygning WHERE ST_Intersects(geom, \'SRID=25832;POLYGON((' + str(TLX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(LRY) + '))\')\"\n')
                                            bat_file.write('ogr2ogr -f \"ESRI Shapefile\" ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=10.34.133.93 port=5432 user=postgres  password=postgres  dbname= dhmqc\" -sql \"select ST_Difference (ST_Union(st_buffer(wkb_geometry, 40)), ST_Union(st_buffer(wkb_geometry,-1))) from geodk.bygning WHERE ST_Intersects(wkb_geometry, \'SRID=25832;POLYGON((' + minX + ' ' + minY + ',' + minX + ' ' + maxY + ',' + maxX + ' ' + maxY + ',' + maxX + ' ' + minY + ',' + minX + ' ' + minY + '))\')\"\n')
                                            bat_file.write("gdal_translate -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:/GDB/DHM/AnvendelseGIS/DSM_20230816.vrt " + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif\n")
                                            bat_file.write('gdal_rasterize -burn -9999 -l ' + ImageID + '_maske ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif\n")
                                            bat_file.write('gdal_translate -a_nodata -9999 ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + "m.tif\n")
                                            #bat_file.write('call  C:/OSGeo4W64/bin/gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                            bat_file.write('call  gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + "m.tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                            bat_file.write('gdal_translate -of AAIGrid ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                    else:
                                        #bat_file.write('ogr2ogr -f \"ESRI Shapefile\" ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=C1507145 port=5432 user= python_script_sdfe  password= python_script_sdfe  dbname= grundkort\" -sql \"select ST_Difference (ST_Union(st_buffer(geom, 40)), ST_Union(st_buffer(geom,-1))) from geodk.bygning WHERE ST_Intersects(geom,  \'SRID=25832;POLYGON((' + str(TLX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(LRY) + '))\')\"\n')
                                        bat_file.write('ogr2ogr -f \"ESRI Shapefile\" ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=10.34.133.93 port=5432 user=postgres  password=postgres  dbname= dhmqc\" -sql \"select ST_Difference (ST_Union(st_buffer(wkb_geometry, 40)), ST_Union(st_buffer(wkb_geometry,-1))) from geodk.bygning WHERE ST_Intersects(wkb_geometry, \'SRID=25832;POLYGON((' + str(TLX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(LRY) + '))\')\"\n')  
                                        bat_file.write("gdal_translate -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(
                                            LRY - (float(RES) * 20)) + " F:/GDB/DHM/AnvendelseGIS/DSM_20230816.vrt " + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif\n")
                                        bat_file.write(
                                            'gdal_rasterize -burn -9999 -l ' + ImageID + '_maske ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif\n")
                                        bat_file.write('gdal_translate -a_nodata -9999 ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + "m.tif\n")
                                        #bat_file.write('call  C:/OSGeo4W64/bin/gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                        bat_file.write('call  gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + "m.tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                        bat_file.write('gdal_translate -of AAIGrid ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")

                                    
                                    #Fix JPEGs for input
                                    #if (((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg')):
                                    #    bat_file.write('gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                    
                                    #always fix jpeg, also in tiffjpeg

                                    nadir = 'gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif -b 1 -b 2 -b 3 -b 4 -co tiled=yes -co blockxsize=256 -co blockysize=256\n"
                                    oblique = 'gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif -b 1 -b 2 -b 3 -co tiled=yes -co blockxsize=256 -co blockysize=256\n"

                                    try:
                                        direction = feat["direction"]
                                        QMessageBox.information(None, "status", f"Direction was: {direction}")
                                        if direction == 'T':
                                            bat_file.write(nadir) ## If the table contain direction attribute and if it is nadir, then write 4 bands
                                        else:
                                             bat_file.write(oblique) ## If the table contain direction attribute and if it is different than nadir, then only write 3 bands
                                    except:
                                        bat_file.write(nadir) ## If the table does not contain direction attribute, we assume the image has 4 bands..

                                    bat_file.write("C:\\dev\\COWS\\orto.exe -def " + defName + "\n")
                                    if self.dlg.radioButton_typ_rgb.isChecked():
                                        TYP = "RGB"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_rgb.tif") + "\n")
                                    elif self.dlg.radioButton_typ_cir.isChecked():
                                        TYP = "CIR"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName.replace(".tif", "_cir.tif") + " " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_cir.tif") + "\n")
                                    elif self.dlg.radioButton_typ_both.isChecked():
                                        TYP = "BOTH"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName.replace(".tif", "_cir.tif") + " " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_cir.tif") + "\n")
                                    else:
                                        TYP = "COMBI"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                    
                                    if self.dlg.checkBoxML.isChecked():
                                        print('kun ortofoto genereres')
                                        #Indsæt hvis der ønsker udklip fra orto# bat_file.write("gdalwarp -t_srs EPSG:25832 -te " + str(TLX) +" " + str(LRY) +" " + str(LRX) +" " + str(TLY)  +" -tr " + str(RES) + " " + str(RES) + " -of GTIFF \"https://services.datafordeler.dk/GeoDanmarkOrto/orto_foraar/1.0.0/WMS?username=PHPJUVTASW&password=Geo123!!&layers=geodanmark_2021_12_5cm_cir&SERVICE=WMS\" " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_OrtoCIR.tif") + "\n")
                                        #Indsæt hvis der ønsker udklip fra orto# bat_file.write("gdalwarp -t_srs EPSG:25832 -te " + str(TLX) +" " + str(LRY) +" " + str(LRX) +" " + str(TLY)  +" -tr " + str(RES) + " " + str(RES) + " -of GTIFF \"https://services.datafordeler.dk/GeoDanmarkOrto/orto_foraar/1.0.0/WMS?username=PHPJUVTASW&password=Geo123!!&layers=geodanmark_2021_12_5cm&SERVICE=WMS\" " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_OrtoRGB.tif") + "\n")

                                        bat_file.write("gdalwarp -t_srs EPSG:25832 -te " + str(TLX) +" " + str(LRY) +" " + str(LRX) +" " + str(TLY)  +" -tr " + str(RES) + " " + str(RES) + " -of GTIFF F:\GDB\DHM\AnvendelseGIS\DSM_20220602.vrt " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_DSM.tif") + "\n")
                                        bat_file.write("gdalwarp -t_srs EPSG:25832 -te " + str(TLX) +" " + str(LRY) +" " + str(LRX) +" " + str(TLY)  +" -tr " + str(RES) + " " + str(RES) + " -of GTIFF F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_DTM.tif") + "\n")



                                    bat_file.write("REM *** Move Output *** \n")
                                    #if self.dlg.checkBoxMinionsOut.isChecked():
                                        #bat_file.write("move " + self.dlg.outDir.text() + "\\" + OName + " F:\\JOB\\DATA\\RemoteSensing\\Drift\\GRU\\orto_output \n")
                                    #bat_file.write("move " + self.dlg.outDir.text() + "\\" + OName + " \\\\10.48.199.207\\Data_8\\Rooftop_full \n")
                                    bat_file.write("move " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "*.*") + " " +self.dlg.outDir_minion.text() + " \n")
                                    #if self.dlg.radioButton_typ_both.isChecked():
                                    #    bat_file.write("move " + self.dlg.outDir.text() + "\\*.*" + " " +self.dlg.outDir_minion.text() + " \n")
                                    bat_file.write("REM *** CleanUP *** \n")
                                    bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\DTM_" + ImageID + "*\n")
                                    bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\" + ImageID + "*\n")
                                    bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\raw_" + ImageID + "*\n")
                                    if self.dlg.checkBoxDelTiff.isChecked():
                                        bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\O" + ImageID + "*\n")


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
                                    #BoBox =QgsGeometry.fromWkt('MULTIPOLYGON ((('+ str(TLX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(TLY) + ')))')
                                    BoBox = 'MULTIPOLYGON (((' + str(TLX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(TLY) + ', ' + str(LRX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(LRY) + ', ' + str(TLX) + ' ' + str(TLY) + ')))'

                                    #QMessageBox.information(None, "bobox",BoBox)

                                    # ***  write BAT file ***
                                    if self.dlg.radioButtonDEM_2007.isChecked():
                                        bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(
                                            LRY - (float(RES) * 20)) + " F:\\GDB\\DHM\\AnvendelseGIS\\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                        # bat_file.write("gdal_translate -of AAIGrid -projwin " + str(float(X_0)-(OSizeX/1.8)) + " " + str(float(Y_0)+(OSizeY/1.8)) + " " + str(float(X_0) + (OSizeX/1.8)) + " " + str(float(Y_0) - (OSizeY/1.8)) + " \\\\c1200038\Data\dtm2007\dtm2007.vrt " + self.lineEdit_workdir.text()+"\\DTM_"+ImageID+".asc\n")
                                    elif self.dlg.radioButtonDEM_2015.isChecked():
                                        if self.dlg.radioButtonDEM_2015.isChecked():
                                            bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:\\GDB\\DHM\\AnvendelseGIS\\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                            # Drunken: bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " " + self.dlg.lineEditDEM.text() + " " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                            #bat_file.write('ogr2ogr -f \"ESRI Shapefile\" ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp pg:\"host=C1507145 port=5432 user= python_script_sdfe  password= python_script_sdfe  dbname= grundkort\" -sql \"select ST_Difference (ST_Union(st_buffer(geom, 40)), ST_Union(st_buffer(geom,-1))) from geodk.bygning WHERE ST_Intersects(geom, \'SRID=25832;POLYGON((' + str(TLX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(TLY) + ',' + str(LRX) + ' ' + str(LRY) + ',' + str(TLX) + ' ' + str(LRY) + '))\')\"\n')
                                            #bat_file.write("gdal_translate -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:/GDB/DHM/AnvendelseGIS/DSM_20190327.vrt " + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif\n")
                                            #bat_file.write('gdal_rasterize -burn -9999 -l ' + ImageID + '_maske ' + self.dlg.lineEdit_workdir.text() + '\\' + ImageID + '_maske.shp ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif\n")
                                            #bat_file.write('gdal_translate -a_nodata -9999 ' + self.dlg.lineEdit_workdir.text() + "\\raw_" + ImageID + ".tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                            #bat_file.write('call  C:/OSGeo4W64/bin/gdal_fillnodata.bat -si 1 ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                            #bat_file.write('gdal_translate -of AAIGrid ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                        else:
                                            bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(LRY - (float(RES) * 20)) + " F:\GDB\DHM\AnvendelseGIS\DTM_orto.vrt " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")
                                            # bat_file.write("gdal_translate -of AAIGrid -projwin " + str(float(X_0)-(OSizeX/1.8)) + " " + str(float(Y_0)+(OSizeY/1.8)) + " " + str(float(X_0) + (OSizeX/1.8)) + " " + str(float(Y_0) - (OSizeY/1.8)) + " \\\\Kms.adroot.dk\dhm2007-server\DHM-E\samlet_20150409.vrt " + self.lineEdit_workdir.text()+"\\DTM_"+ImageID+".asc\n")

                                    elif self.dlg.radioButtonDEM_spec.isChecked():
                                        bat_file.write("gdal_translate -of AAIGrid -projwin " + str(TLX - (float(RES) * 20)) + " " + str(TLY + (float(RES) * 20)) + " " + str(LRX + (float(RES) * 20)) + " " + str(
                                            LRY - (float(RES) * 20)) + " " +self.dlg.lineEditDEM.text()+ " " + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".asc\n")

                                    else:
                                        pass

                                    # create tif file for processing
                                    # if (self.dlg.radioButton_fieldpath.isChecked() and ((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg')):
                                    #if (((os.path.splitext(str(feat[self.dlg.inField1.currentText()]))[1]).lower() == '.jpg')):
                                    #    bat_file.write('gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif\n")
                                    #always fix jpeg, also in tiffjpeg

                                    nadir = 'gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif -b 1 -b 2 -b 3 -b 4 -co tiled=yes -co blockxsize=256 -co blockysize=256\n"
                                    oblique = 'gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif -b 1 -b 2 -b 3 -co tiled=yes -co blockxsize=256 -co blockysize=256\n"

                                    try:
                                        direction = feat["direction"]
                                        #QMessageBox.information(None, "status", f"Direction was: {direction}")
                                        if direction == 'T':
                                            bat_file.write(nadir) ## If the table contain direction attribute and if it is nadir, then write 4 bands
                                        else:
                                             bat_file.write(oblique) ## If the table contain direction attribute and if it is different than nadir, then only write 3 bands
                                    except:
                                        bat_file.write(nadir) ## If the table does not contain direction attribute, we assume the image has 4 bands..
                                    #bat_file.write('gdal_translate -of GTiff ' + str(feat[self.dlg.inField1.currentText()]) + ' ' + self.dlg.lineEdit_workdir.text() + "\\DTM_" + ImageID + ".tif -b 1 -b 2 -b 3 -b 4 -co tiled=yes -co blockxsize=256 -co blockysize=256\n")

                                    if self.dlg.checkBoxGoGoMinions.isChecked():
                                        bat_file.write("C:\\dev\\COWS\\orto.exe -def " + defName + "\n")
                                    else:
                                        bat_file.write(os.path.dirname(__file__) + "\\orto.exe -def " + self.dlg.outDir.text() + "\\" + ImageID + ".def\n")
                                    bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\DTM_" + ImageID + "*\n")
                                    if self.dlg.radioButton_typ_rgb.isChecked():
                                        TYP = "RGB"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                    elif self.dlg.radioButton_typ_cir.isChecked():
                                        TYP = "CIR"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName.replace(".tif", "_cir.tif") + " " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_cir.tif") + "\n")
                                    elif self.dlg.radioButton_typ_both.isChecked():
                                        TYP = "BOTH"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName.replace(".tif", "_cir.tif") + " " + self.dlg.outDir.text() + "\\" + OName.replace(".tif", "_cir.tif") + "\n")
                                    else:
                                        TYP = "COMBI"
                                        bat_file.write("gdal_translate -b 1 -b 2 -b 3 -a_srs EPSG:25832 -of GTIFF -co COMPRESS=JPEG -co JPEG_QUALITY=85 -co PHOTOMETRIC=YCBCR -co TILED=YES " + self.dlg.lineEdit_workdir.text() + "\\" + OName + " " + self.dlg.outDir.text() + "\\" + OName + "\n")
                                    
                                    if self.dlg.checkBoxDelTiff.isChecked():
                                        bat_file.write("del " + (self.dlg.lineEdit_workdir.text()).replace('/', '\\') + "\\O" + ImageID + "*\n")




                            # *** write DEF file ***
                            rs.createDef(defName, imgpath, DEMpath, ortName, IO, EO, Polyg, RES, TYP)
                            if self.dlg.checkBoxGoGoMinions.isChecked():
                                #rs.MinionManager('quick_orto', orto_batfil, CHKuser, BoBox)
                                rs.MinionManager('orto_ml', orto_batfil, CHKuser, BoBox)

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
                            #QMessageBox.information(None, "Status","DEF and Batfile created. \n\nPlease run " + self.dlg.lineEdit_workdir.text() + "\\" + self.dlg.inShapeA.currentText() + ".bat from a OSGEO4W shell")
                            QMessageBox.information(None, "Status",f"DEF and Batfile created. \n\nPlease run {self.dlg.lineEdit_workdir.text()}\\{self.dlg.inShapeA.currentText()}.bat from a OSGEO4W shell\n\nFYI: inner orientations found in table: {inner_ori_table}")
                            #QMessageBox.information(None, "status", f"Inner orientations found in table: {inner_ori_table}\n\nFound other directions than T: {dir_not_T}")

                pass
