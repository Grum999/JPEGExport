# -----------------------------------------------------------------------------
# JPEG Export
# Copyright (C) 2024 - Grum999
# -----------------------------------------------------------------------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see https://www.gnu.org/licenses/
# -----------------------------------------------------------------------------
# A Krita plugin designed to export as JPEG with a preview of final result
# -----------------------------------------------------------------------------

from jpegexport.pktk.modules.utils import loadXmlUi
import os
import os.path
import sys

from PyQt5.Qt import *
from PyQt5.QtWidgets import (
        QWidget
    )
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

from .jesettings import JESettingsKey

from jpegexport.pktk.widgets.wiodialog import WDialogFile

from ..pktk import *


# -----------------------------------------------------------------------------
class WJEPathOptions(QWidget):
    """A basic QWidget used to manage path options"""
    pathUpdated = Signal()

    MODE_SRC = 'src'
    MODE_USR = 'usr'
    MODE_LST = 'lst'

    def __init__(self, parent=None):
        super(WJEPathOptions, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), 'resources', 'wjepathoptions.ui')

        # temporary add <plugin> path to sys.path to let 'pktk.widgets.xxx' being accessible during xmlLoad()
        # because of WColorButton path that must be absolut in UI file
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        loadXmlUi(uiFileName, self)

        # remove temporary added path
        sys.path.pop()

        self.__initialiseUi()

    def __initialiseUi(self):
        """Initialise widget interface"""
        self.rbTgtPathSrc.toggled.connect(self.__tgtPathUpdated)
        self.rbTgtPathLst.toggled.connect(self.__tgtPathUpdated)
        self.rbTgtPathUsr.toggled.connect(self.__tgtPathUpdated)
        self.tbSelectPath.clicked.connect(self.__selectUsrPath)
        self.leFileName.mouseDoubleClickEvent = lambda x: self.__selectUsrPath()
        self.__tgtPathUpdated(None)

    def __tgtPathUpdated(self, value):
        """Target path mode updated

        Update UI, emit signal
        """
        self.leFileName.setEnabled(self.rbTgtPathUsr.isChecked())
        self.tbSelectPath.setEnabled(self.rbTgtPathUsr.isChecked())
        self.pathUpdated.emit()

    def __selectUsrPath(self, value=None):
        """Open folder dialog box

        Update UI, emit signal
        """
        if returned := WDialogFile.openDirectory(i18n("Select target directory"), self.leFileName.text()):
            self.leFileName.setText(returned['directory'])
            self.pathUpdated.emit()

    def property(self, key):
        """Return property value for `key`"""
        if key == JESettingsKey.CONFIG_PATH_TGTMODE:
            # mode
            if self.rbTgtPathSrc.isChecked():
                return WJEPathOptions.MODE_SRC
            elif self.rbTgtPathLst.isChecked():
                return WJEPathOptions.MODE_LST
            else:
                return WJEPathOptions.MODE_USR
        elif key == JESettingsKey.CONFIG_PATH_USRPATH:
            # user path
            return self.leFileName.text()

    def setProperty(self, key, value):
        """Set property defined by `key`

        Available keys:
            JESettingsKey.CONFIG_PATH_TGTMODE
            JESettingsKey.CONFIG_PATH_USRPATH
        """
        if key == JESettingsKey.CONFIG_PATH_TGTMODE:
            if value == WJEPathOptions.MODE_SRC:
                self.rbTgtPathSrc.setChecked(True)
            elif value == WJEPathOptions.MODE_LST:
                self.rbTgtPathLst.setChecked(True)
            else:
                self.rbTgtPathUsr.setChecked(True)
        elif key == JESettingsKey.CONFIG_PATH_USRPATH:
            self.leFileName.setText(value)

    def setProperties(self, properties):
        """Set properties from a dictionary"""
        if not isinstance(properties, dict):
            raise EInvalidType("Given `properties` must be a <dict>")

        for propertyKey in (JESettingsKey.CONFIG_PATH_TGTMODE,
                            JESettingsKey.CONFIG_PATH_USRPATH):
            if propertyKey in properties:
                self.setProperty(propertyKey, properties[propertyKey])

