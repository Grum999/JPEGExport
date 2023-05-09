#-----------------------------------------------------------------------------
# JPEG Export
# Copyright (C) 2020 - Grum999
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

import os
import re
import sys
import time

import PyQt5.uic

from krita import (
        Extension,
        Krita
    )

from PyQt5.Qt import *
from PyQt5 import QtCore
from PyQt5.QtCore import (
        pyqtSlot
    )

if __name__ != '__main__':
     # script is executed from Krita, loaded as a module
    __PLUGIN_EXEC_FROM__ = 'KRITA'

    from .pktk.pktk import (
            EInvalidStatus,
            EInvalidType,
            EInvalidValue,
            PkTk
        )
    from jpegexport.pktk.modules.utils import checkKritaVersion
    from jpegexport.pktk.modules.uitheme import UITheme
    from jpegexport.je.jemainwindow import JEMainWindow
else:
    # Execution from 'Scripter' plugin?
    __PLUGIN_EXEC_FROM__ = 'SCRIPTER_PLUGIN'

    from importlib import reload

    print("======================================")
    print(f'Execution from {__PLUGIN_EXEC_FROM__}')

    for module in list(sys.modules.keys()):
        if not re.search(r'^jpegexport\.', module) is None:
            print('Reload module {0}: {1}', module, sys.modules[module])
            reload(sys.modules[module])

    from jpegexport.pktk.pktk import (
            EInvalidStatus,
            EInvalidType,
            EInvalidValue,
            PkTk
        )
    from jpegexport.pktk.modules.utils import checkKritaVersion
    from jpegexport.pktk.modules.uitheme import UITheme
    from jpegexport.je.jemainwindow import JEMainWindow

    print("======================================")


EXTENSION_ID = 'pykrita_jpegexport'
PLUGIN_VERSION = '1.2.1'
PLUGIN_MENU_ENTRY = 'JPEG Export'

REQUIRED_KRITA_VERSION = (5, 2, 0)

PkTk.setPackageName('jpegexport')


class JpegExport(Extension):

    def __init__(self, parent):
        # Default options

        # Always initialise the superclass.
        # This is necessary to create the underlying C++ object
        super(JpegExport, self).__init__(parent)
        self.parent = parent
        self.__uiController = None
        self.__isKritaVersionOk = checkKritaVersion(*REQUIRED_KRITA_VERSION)
        self.__dlgParentWidget = QWidget()
        self.__action = None
        self.__notifier = Krita.instance().notifier()


    def __windowCreated(self):
        """Main window has been created"""
        def aboutToShowFileMenu():
            self.__action.setEnabled(len(Krita.instance().activeWindow().views()) > 0)

        menuFile = None
        actionRef = None

        # search for menu 'File'
        menuFile = Krita.instance().activeWindow().qwindow().findChild(QMenu,'file')

        if isinstance(menuFile, QMenu):
            # search for 'Export Advanced...' action
            actionRef = Krita.instance().action('file_export_advanced')

            if actionRef:
                # move action to right place
                menuFile.removeAction(self.__action)
                menuFile.insertAction(actionRef, self.__action)
            else:
                # not found??
                # fallback
                actionRef = Krita.instance().action('file_export_file')

                getNext = False
                for action in menuFile.actions():
                    if action.objectName() == 'file_export_file':
                        getNext = True
                    elif getNext:
                        actionRef = action
                        break

            if actionRef:
                # move action to right place
                menuFile.removeAction(self.__action)
                menuFile.insertAction(actionRef, self.__action)
            else:
                qError('Unable to find <file_export_advanced> neither <file_export_file>!')

            # update icon
            self.__action.setIcon(QIcon(actionRef.icon()))

            # by default, set menu disabled
            self.__action.setEnabled(False)

            menuFile.aboutToShow.connect(aboutToShowFileMenu)

    def setup(self):
        """Is executed at Krita's startup"""
        if not self.__isKritaVersionOk:
            return

        if checkKritaVersion(5,0,0):
            UITheme.load()

            self.__notifier.setActive(True)
            self.__notifier.windowCreated.connect(self.__windowCreated)


    def createActions(self, window):
        if checkKritaVersion(5,0,0):
            self.__action = window.createAction(EXTENSION_ID, f'{PLUGIN_MENU_ENTRY}...', "file")
        else:
            self.__action = window.createAction(EXTENSION_ID, f'{PLUGIN_MENU_ENTRY}...', "tools/scripts")
        self.__action.triggered.connect(self.start)

    def start(self):
        """Execute JPEG Export"""
        # ----------------------------------------------------------------------
        # Create dialog box
        if not self.__isKritaVersionOk:
            QMessageBox.information(QWidget(),
                                      PLUGIN_MENU_ENTRY,
                                      "At least, Krita version {0} is required to use plugin...".format('.'.join([str(v) for v in REQUIRED_KRITA_VERSION]))
                                    )
            return

        JEMainWindow(PLUGIN_MENU_ENTRY, PLUGIN_VERSION, self.__dlgParentWidget)

if __PLUGIN_EXEC_FROM__ == 'SCRIPTER_PLUGIN':
    sys.stdout = sys.__stdout__

    # Disconnect signals if any before assigning new signals
    ch = JpegExport(Krita.instance())
    ch.setup()
    ch.start()
