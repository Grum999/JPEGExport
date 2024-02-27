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

from .jesettings import (
        JESettingsKey,
        JESettingsValues
    )

from ..pktk import *


# -----------------------------------------------------------------------------
class WJEContentOptions(QWidget):
    """A basic QWidget used to manage content options (crop & resize)"""
    docUpdate = Signal()                   # when need to update document
    sizeUpdate = Signal(bool)              # when need to recalculate document size

    RESIZE_METHOD = [
            (i18n('B-Spline'),          JESettingsValues.FILTER_BSPLINE),
            ('Bell',                    JESettingsValues.FILTER_BELL),
            (i18n('Bicubic'),           JESettingsValues.FILTER_BICUBIC),
            (i18n('Bilinear'),          JESettingsValues.FILTER_BILINEAR),
            ('Hermite',                 JESettingsValues.FILTER_HERMITE),
            (i18n('Lancsoz3'),          JESettingsValues.FILTER_LANCZOS3),
            ('Mitchell',                JESettingsValues.FILTER_MITCHELL),
            (i18n('Nearest neighbour'), JESettingsValues.FILTER_NEAREST_NEIGHBOUR)
        ]

    def __init__(self, parent=None):
        super(WJEContentOptions, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), 'resources', 'wjecontentoptions.ui')

        # temporary add <plugin> path to sys.path to let 'pktk.widgets.xxx' being accessible during xmlLoad()
        # because of WColorButton path that must be absolut in UI file
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        loadXmlUi(uiFileName, self)

        # remove temporary added path
        sys.path.pop()

        self.__initialiseUi()

    def __initialiseUi(self):
        """Initialise widget interface"""
        # crop
        self.cbxResizedUnit.addItem('px', 'px')
        self.cbxResizedUnit.addItem('%', '%')
        self.cbxResizedUnit.addItem('px (width)', 'wpx')
        self.cbxResizedUnit.addItem('px (height)', 'hpx')

        for index, value in enumerate(WJEContentOptions.RESIZE_METHOD):
            self.cbxResizeFilter.addItem(value[0], value[1])

        self.cbCropToSelection.toggled.connect(lambda x: self.docUpdate.emit())
        self.cbResizeDocument.toggled.connect(lambda x: self.sizeUpdate.emit(True))
        self.cbResizeDocument.toggled.connect(lambda value: self.wResizeOptions.setEnabled(value))
        self.cbxResizedUnit.currentIndexChanged.connect(lambda x: self.__updateResizeUnit(True))
        self.cbxResizeFilter.currentIndexChanged.connect(lambda x: self.sizeUpdate.emit(False))
        self.sbResizedMaxWidth.valueChanged.connect(lambda x: self.sizeUpdate.emit(False))
        self.sbResizedMaxHeight.valueChanged.connect(lambda x: self.sizeUpdate.emit(False))
        self.dsbResizePct.valueChanged.connect(lambda x: self.sizeUpdate.emit(False))

    def showEvent(self, event):
        """Dialog is visible"""
        # define minimum width for pct input value, according to current width defined for width/height input values
        self.dsbResizePct.setMinimumWidth(self.sbResizedMaxWidth.width()+self.sbResizedMaxHeight.width()+self.lblResizeX.width())
        self.dsbResizePct.setMaximumWidth(self.sbResizedMaxWidth.width()+self.sbResizedMaxHeight.width()+self.lblResizeX.width())
        self.__updateResizeUnit(False)

    def property(self, key):
        """Return property value for `key`"""
        if key == JESettingsKey.CONFIG_MISC_CROP_ACTIVE:
            # crop
            return self.cbCropToSelection.isChecked()
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE:
            # resize
            return self.cbResizeDocument.isChecked()
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_FILTER:
            return self.cbxResizeFilter.currentData()
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE:
            return self.dsbResizePct.value()
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH:
            return self.sbResizedMaxWidth.value()
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT:
            return self.sbResizedMaxHeight.value()
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_UNIT:
            return self.cbxResizedUnit.currentData()

    def setProperty(self, key, value):
        """Set property defined by `key`

        Available keys:
            JESettingsKey.CONFIG_MISC_CROP_ACTIVE
            JESettingsKey.CONFIG_MISC_RESIZE_UNIT
            JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE
            JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE
            JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH
            JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT
        """
        if key == JESettingsKey.CONFIG_MISC_CROP_ACTIVE:
            # crop
            self.cbCropToSelection.setChecked(value)
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE:
            # resize
            self.cbResizeDocument.setChecked(value)
            self.wResizeOptions.setEnabled(value)
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_FILTER:
            for index, methodValue in enumerate(WJEContentOptions.RESIZE_METHOD):
                if methodValue[1] == value:
                    self.cbxResizeFilter.setCurrentIndex(index)
                    break
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE:
            self.dsbResizePct.setValue(value)
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH:
            self.sbResizedMaxWidth.setValue(value)
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT:
            self.sbResizedMaxHeight.setValue(value)
        elif key == JESettingsKey.CONFIG_MISC_RESIZE_UNIT:
            self.cbxResizedUnit.setCurrentIndex(self.__cbxIndexForUnit(value))

    def setProperties(self, properties):
        """Set properties from a dictionary"""
        if not isinstance(properties, dict):
            raise EInvalidType("Given `properties` must be a <dict>")

        for propertyKey in (JESettingsKey.CONFIG_MISC_CROP_ACTIVE,
                            JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE,
                            JESettingsKey.CONFIG_MISC_RESIZE_FILTER,
                            JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE,
                            JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH,
                            JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT,
                            JESettingsKey.CONFIG_MISC_RESIZE_UNIT):
            if propertyKey in properties:
                self.setProperty(propertyKey, properties[propertyKey])

    def setDocSelection(self, selection=None):
        """Define if current document have a selection

        If not, 'crop' option is disabled
        """
        if selection:
            self.cbCropToSelection.setEnabled(True)
            self.cbCropToSelection.setText(i18n("Crop to selection")+f" ({selection.width()}x{selection.height()})")
        else:
            self.cbCropToSelection.setEnabled(False)

    def hasDocSelection(self):
        """return true if document have a selection (means: crop to selection option is active)"""
        return self.cbCropToSelection.isEnabled()

    def __updateResizeUnit(self, updateSize=True):
        """Unit has been modified (px, %, wpx, hpx)

        Update width/height according to unit
        """
        if self.cbxResizedUnit.currentData() == JESettingsValues.UNIT_PX:
            # to 'px'
            self.dsbResizePct.setVisible(False)
            self.sbResizedMaxWidth.setVisible(True)
            self.lblResizeX.setVisible(True)
            self.sbResizedMaxHeight.setVisible(True)
        elif self.cbxResizedUnit.currentData() == JESettingsValues.UNIT_PCT:
            # to '%'
            self.sbResizedMaxWidth.setVisible(False)
            self.lblResizeX.setVisible(False)
            self.sbResizedMaxHeight.setVisible(False)
            self.dsbResizePct.setVisible(True)
        elif self.cbxResizedUnit.currentData() == JESettingsValues.UNIT_PX_WIDTH:
            # to 'wpx'
            self.dsbResizePct.setVisible(False)
            self.sbResizedMaxWidth.setVisible(True)
            self.lblResizeX.setVisible(False)
            self.sbResizedMaxHeight.setVisible(False)
        elif self.cbxResizedUnit.currentData() == JESettingsValues.UNIT_PX_HEIGHT:
            # to 'hpx'
            self.dsbResizePct.setVisible(False)
            self.sbResizedMaxWidth.setVisible(False)
            self.lblResizeX.setVisible(False)
            self.sbResizedMaxHeight.setVisible(True)

        if updateSize:
            self.sizeUpdate.emit(False)

    def __cbxIndexForUnit(self, unit):
        """Return index for given unit for cbxResizedUnit

        Otherwise return None
        """
        for index in range(self.cbxResizedUnit.count()):
            if self.cbxResizedUnit.itemData(index) == unit:
                return index
        return None
