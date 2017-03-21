
# -*- coding: utf-8 -*-
import os

from PyQt4 import QtGui, uic
from qgissettingmanager import SettingManager, SettingDialog
from qgissettingmanager.types import String
from qgissettingmanager.setting import Scope

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'ortho_maker_settings.ui')
)

class OrthoMakerSettings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, 'OrthoMaker')
        self.add_setting(String('database', Scope.Global, ''))
        self.add_setting(String('hostname', Scope.Global, ''))
        self.add_setting(String('username', Scope.Global, ''))
        self.add_setting(String('password', Scope.Global, ''))
        self.add_setting(String('port', Scope.Global, '5432'))



class OrthoMakerSettingsDialog(QtGui.QDialog, FORM_CLASS, SettingDialog):
    def __init__(self, settings):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        SettingDialog.__init__(self, settings)
