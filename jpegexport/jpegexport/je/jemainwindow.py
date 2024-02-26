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


import os
import os.path
import re
import shutil
import sys
from krita import Krita

from PyQt5.Qt import *
from PyQt5.QtWidgets import (
        QWidget
    )

from .jesettings import (
        JESettings,
        JESettingsKey,
        JESettingsValues
    )

from jpegexport.pktk.modules.utils import loadXmlUi
from jpegexport.pktk.modules.strutils import bytesSizeToStr
from jpegexport.pktk.modules.imgutils import (imgBoxSize,
                                              buildIcon
                                              )
from jpegexport.pktk.modules.timeutils import Timer
from jpegexport.pktk.widgets.wefiledialog import WEFileDialog
from jpegexport.pktk.widgets.wabout import WAboutWindow
from jpegexport.pktk.widgets.wedialog import WEDialog

from jpegexport.pktk.modules.ekrita import (
        EKritaWindow,
        EKritaDocument,
        EKritaNode
    )

from jpegexport.pktk import *

# -----------------------------------------------------------------------------
class JEViewer(QWidget):
    """A basic QWidget used to display setups"""

    def __init__(self, parent=None):
        super(JEViewer, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), 'resources', 'jesettingsviewer.ui')

        # temporary add <plugin> path to sys.path to let 'xxx.widgets.xxx' being accessible during xmlLoad()
        # because of WColorButton path that must be absolut in UI file
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        loadXmlUi(uiFileName, self)

        # remove temporary added path
        sys.path.pop()

    def setData(self, data):
        """Data to preview"""
        self.wJpegOptions.setOptions({
                'quality': data[JESettingsKey.CONFIG_JPEG_QUALITY.id()],
                'smoothing': data[JESettingsKey.CONFIG_JPEG_SMOOTHING.id()],
                'subsampling': data[JESettingsKey.CONFIG_JPEG_SUBSAMPLING.id()],
                'progressive': data[JESettingsKey.CONFIG_JPEG_PROGRESSIVE.id()],
                'optimize': data[JESettingsKey.CONFIG_JPEG_OPTIMIZE.id()],
                'saveProfile': data[JESettingsKey.CONFIG_JPEG_SAVEPROFILE.id()],
                'transparencyFillcolor': data[JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR.id()]
            })

        self.wContentOptions.setProperties({
                JESettingsKey.CONFIG_MISC_CROP_ACTIVE: data[JESettingsKey.CONFIG_MISC_CROP_ACTIVE.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE: data[JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_FILTER: data[JESettingsKey.CONFIG_MISC_RESIZE_FILTER.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE: data[JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH: data[JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT: data[JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_UNIT: data[JESettingsKey.CONFIG_MISC_RESIZE_UNIT.id()]
                })


# -----------------------------------------------------------------------------
class JEMainWindow(WEDialog):
    """Main JpegExport window"""

    PAGE_OPTCONTENT = 0
    PAGE_JPEGEXPORT = 1

    # A flag to ensure that class is instancied only once
    __IS_OPENED = False

    # delay between modified properties and preview update
    __UPDATE_DELAY = 375
    __RESIZE_DELAY = 625

    __MAX_WIDTH_AND_HEIGHT = 32000

    __UPDATE_MODE_CROP =   0b00000001
    __UPDATE_MODE_RESIZE = 0b00000010

    def __init__(self, jeName="JPEG Export", jeVersion="testing", parent=None):
        super(JEMainWindow, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'jemainwindow.ui'), parent)

        self.__notifier = None

        # another instance already exist, exit
        if JEMainWindow.__IS_OPENED:
            self.close()
            return

        self.__accepted = False

        self.__timerPreview = 0                   # timer used for preview update
        self.__timerResize = 0                    # timer used for resize update

        self.__tmpDoc = None                      # internal document used for export (not added to view)
        self.__tmpDocTgtNode = None
        self.__tmpDocPreview = None               # document used for preview (added to view)
        self.__tmpDocPreviewFileNode = None
        self.__tmpDocPreviewSrcNode = None

        self.__jeName = jeName
        self.__jeVersion = jeVersion

        self.__viewScrollbarH = None
        self.__viewScrollbarV = None
        self.__positionFull = None
        self.__positionCrop = None

        self.__doc = Krita.instance().activeDocument()
        self.__boundsSource = None
        self.__sizeTarget = None

        self.__pgOptContent = QListWidgetItem(buildIcon("pktk:image_crop"), i18n("Exported content"))
        self.__pgOptContent.setData(Qt.UserRole, JEMainWindow.PAGE_OPTCONTENT)
        self.__pgOptJpegExport = QListWidgetItem(buildIcon("pktk:tune_img_slider"), i18n("JPEG Options"))
        self.__pgOptJpegExport.setData(Qt.UserRole, JEMainWindow.PAGE_JPEGEXPORT)

        if self.__doc is None:
            # no document opened: cancel plugin
            QMessageBox.warning(QWidget(),
                                f"{jeName}",
                                i18n("There's no active document: <i>JPEG Export</i> plugin only works with opened documents")
                                )
            self.close()
            return

        JEMainWindow.__IS_OPENED = True

        basename, ext = os.path.splitext(os.path.basename(self.__doc.fileName()))
        self.__tmpExportPreviewFile = os.path.join(QDir.tempPath(), f'{basename} (JPEG Export Preview).jpeg')
        self.__tmpExportFile = os.path.join(QDir.tempPath(), f'jpegexport-{QUuid.createUuid().toString(QUuid.Id128)}.jpeg')
        self.__docFileName = self.__doc.fileName()

        self.__notifier = Krita.instance().notifier()
        self.__notifier.imageClosed.connect(self.__imageClosed)

        self.setModal(False)
        self.setWindowTitle(i18n(f'{jeName} v{jeVersion}'))
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

        self.__initialiseUi()
        self.__initialiseDoc()

        self.show()

    def __initialiseDoc(self):
        """Initialise temporary document"""
        self.__calculateBounds()

        # The __tmpDoc contain a flatened copy of current document
        self.__tmpDoc = Krita.instance().createDocument(self.__boundsSource.width(),
                                                        self.__boundsSource.height(),
                                                        "Jpeg Export - Temporary preview",
                                                        self.__doc.colorModel(),
                                                        self.__doc.colorDepth(),
                                                        self.__doc.colorProfile(),
                                                        self.__doc.resolution())
        self.__tmpDocTgtNode = self.__tmpDoc.createNode("Preview", "paintlayer")
        self.__tmpDoc.rootNode().addChildNode(self.__tmpDocTgtNode, None)
        self.__tmpDoc.setBatchmode(True)
        # force jpeg export
        self.timerEvent(None)

        # The __tmpDocPreview contain the Jpeg file for preview
        self.__tmpDocPreview = Krita.instance().createDocument(self.__boundsSource.width(),
                                                               self.__boundsSource.height(),
                                                               "Jpeg Export - Temporary preview",
                                                               self.__doc.colorModel(),
                                                               self.__doc.colorDepth(),
                                                               self.__doc.colorProfile(),
                                                               self.__doc.resolution())
        # add original document content, as reference for diff
        self.__tmpDocPreviewSrcNode = self.__tmpDocPreview.createNode("Source", "paintlayer")
        self.__tmpDocPreview.rootNode().addChildNode(self.__tmpDocPreviewSrcNode, None)
        # add file layer linked to exported jpeg document, to see preview
        self.__tmpDocPreviewFileNode = self.__tmpDocPreview.createFileLayer("Preview", self.__tmpExportFile, "None")
        self.__tmpDocPreview.rootNode().addChildNode(self.__tmpDocPreviewFileNode, None)
        self.__tmpDocPreview.setBatchmode(True)
        self.__tmpDocPreview.setFileName(self.__tmpExportPreviewFile)

        Krita.instance().activeWindow().addView(self.__tmpDocPreview)  # shows it in the application

        # self.lblDocDimension.setText(i18n(f"Dimensions: {self.__tmpDoc.width()}x{self.__tmpDoc.height()}"))

        scrollbars = EKritaWindow.scrollbars()
        if scrollbars:
            self.__viewScrollbarH, self.__viewScrollbarV = scrollbars
            self.__viewScrollbarH.sliderMoved.connect(self.__updatePosition)
            self.__viewScrollbarV.sliderMoved.connect(self.__updatePosition)
            self.__updatePosition()

        self.__updateDoc()
        self.__renderModeChanged()

    def __initialiseUi(self):
        """Initialise window interface"""
        JESettings.load()

        self.twMain.setCurrentIndex(0)

        self.wJpegOptions.setOptions({
                'quality': JESettings.get(JESettingsKey.CONFIG_JPEG_QUALITY),
                'smoothing': JESettings.get(JESettingsKey.CONFIG_JPEG_SMOOTHING),
                'subsampling': JESettings.get(JESettingsKey.CONFIG_JPEG_SUBSAMPLING),
                'progressive': JESettings.get(JESettingsKey.CONFIG_JPEG_PROGRESSIVE),
                'optimize': JESettings.get(JESettingsKey.CONFIG_JPEG_OPTIMIZE),
                'saveProfile': JESettings.get(JESettingsKey.CONFIG_JPEG_SAVEPROFILE),
                'transparencyFillcolor': JESettings.get(JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR)
                })

        self.wContentOptions.setProperties({
                JESettingsKey.CONFIG_MISC_CROP_ACTIVE: JESettings.get(JESettingsKey.CONFIG_MISC_CROP_ACTIVE),
                JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE: JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE),
                JESettingsKey.CONFIG_MISC_RESIZE_FILTER: JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_FILTER),
                JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE: JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE),
                JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH: JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH),
                JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT: JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT),
                JESettingsKey.CONFIG_MISC_RESIZE_UNIT: JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_UNIT)
                })

        newFileName = self.__doc.fileName()
        if newFileName == '':
            newFileName = os.path.join(JESettings.get(JESettingsKey.CONFIG_FILE_LASTPATH), 'newDocument.jpeg')
        else:
            newFileName = re.sub(r'\.[^.]+$', '.jpeg', newFileName)

        self.leFileName.setText(newFileName)

        renderMode = JESettings.get(JESettingsKey.CONFIG_RENDER_MODE)
        if renderMode == JESettingsValues.RENDER_MODE_FINAL:
            self.rbRenderNormal.setChecked(True)
        elif renderMode == JESettingsValues.RENDER_MODE_DIFFVALUE:
            self.rbRenderDifference.setChecked(True)
        elif renderMode == JESettingsValues.RENDER_MODE_DIFFBITS:
            self.rbRenderXOR.setChecked(True)
        elif renderMode == JESettingsValues.RENDER_MODE_SOURCE:
            self.rbRenderSrc.setChecked(True)

        # window geometry
        sizeW = JESettings.get(JESettingsKey.CONFIG_WINDOW_GEOMETRY_SIZE_WIDTH)
        sizeH = JESettings.get(JESettingsKey.CONFIG_WINDOW_GEOMETRY_SIZE_HEIGHT)
        positionX = JESettings.get(JESettingsKey.CONFIG_WINDOW_GEOMETRY_POSITION_X)
        positionY = JESettings.get(JESettingsKey.CONFIG_WINDOW_GEOMETRY_POSITION_Y)
        # geometry is taken in account only if size > 0 (otherwise, mean that value weren't initialized)
        if sizeH > 0 and sizeW > 0:
            self.setGeometry(positionX, positionY, sizeW, sizeH)

        # setup manager
        self.wsmSetups.setupApplied.connect(self.__applySetupFromManager)
        self.wsmSetups.setPropertiesEditorSetupPreviewWidgetClass(JEViewer)
        self.wsmSetups.setExtensionFilter(f"{i18n('JPEG Export Setups')} (*.jesetups)")
        self.wsmSetups.setStoredDataFormat('je--export_setup', '1.0.0')
        self.wsmSetups.setIconSizeIndex(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_ZOOMLEVEL))
        self.wsmSetups.setColumnSetupWidth(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLUMNWIDTH))
        self.wsmSetups.setPropertiesEditorIconSelectorViewMode(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_VIEWMODE))
        self.wsmSetups.setPropertiesEditorIconSelectorIconSizeIndex(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_ZOOMLEVEL))
        self.wsmSetups.setPropertiesEditorColorPickerLayout(JESettings.getTxtColorPickerLayout())

        lastSetupFileName = JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_LASTFILE)
        if lastSetupFileName != '' and os.path.exists(lastSetupFileName):
            self.wsmSetups.openSetup(lastSetupFileName, False)
        else:
            lastSetupFileName = os.path.join(QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation), f'krita-plugin-{PkTk.packageName()}-default.jesetups')
            self.wsmSetups.newSetups(True)
            self.wsmSetups.saveSetup(lastSetupFileName, 'Default JPEG Export Setups')

        self.wsmSetups.setIconUri('pktk:tune_img_slider')

        # pages
        self.lvPages.addItem(self.__pgOptContent)
        self.lvPages.addItem(self.__pgOptJpegExport)

        # signals
        self.wContentOptions.docUpdate.connect(lambda: self.__updateDoc(JEMainWindow.__UPDATE_MODE_CROP))
        self.wContentOptions.sizeUpdate.connect(lambda immediate: self.__updateNewSize(immediate))
        self.wJpegOptions.optionUpdated.connect(self.__updatePreview)

        self.pbOk.clicked.connect(self.__acceptChange)
        self.pbCancel.clicked.connect(self.__rejectChange)
        self.pbAbout.clicked.connect(self.__displayAbout)

        self.rbRenderNormal.toggled.connect(self.__renderModeChanged)
        self.rbRenderDifference.toggled.connect(self.__renderModeChanged)
        self.rbRenderXOR.toggled.connect(self.__renderModeChanged)
        self.rbRenderSrc.toggled.connect(self.__renderModeChanged)

        self.lvPages.itemSelectionChanged.connect(self.__pageChanged)

        self.tbSaveAs.clicked.connect(self.__saveFileName)
        self.leFileName.mouseDoubleClickEvent = lambda x: self.__saveFileName()

        self.__setPage(JEMainWindow.PAGE_OPTCONTENT)

    def __pageChanged(self):
        """Set page according to option"""
        self.swPages.setCurrentIndex(self.lvPages.currentItem().data(Qt.UserRole))

    def __setPage(self, value):
        """Set page setting

        Select icon, switch to panel
        """
        self.lvPages.setCurrentRow(value)

    def __applySetupFromManager(self, setupManagerSetup):
        data = setupManagerSetup.data()
        self.wJpegOptions.setOptions({
                'quality': data[JESettingsKey.CONFIG_JPEG_QUALITY.id()],
                'smoothing': data[JESettingsKey.CONFIG_JPEG_SMOOTHING.id()],
                'subsampling': data[JESettingsKey.CONFIG_JPEG_SUBSAMPLING.id()],
                'progressive': data[JESettingsKey.CONFIG_JPEG_PROGRESSIVE.id()],
                'optimize': data[JESettingsKey.CONFIG_JPEG_OPTIMIZE.id()],
                'saveProfile': data[JESettingsKey.CONFIG_JPEG_SAVEPROFILE.id()],
                'transparencyFillcolor': data[JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR.id()]
                })

        self.wContentOptions.setProperties({
                JESettingsKey.CONFIG_MISC_CROP_ACTIVE: data[JESettingsKey.CONFIG_MISC_CROP_ACTIVE.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE: data[JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_FILTER: data[JESettingsKey.CONFIG_MISC_RESIZE_FILTER.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE: data[JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH: data[JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT: data[JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT.id()],
                JESettingsKey.CONFIG_MISC_RESIZE_UNIT: data[JESettingsKey.CONFIG_MISC_RESIZE_UNIT.id()]
                })

    def __setupData(self):
        """Return a dict with current setup data"""
        jpegOptions = self.wJpegOptions.options()

        returned = {JESettingsKey.CONFIG_JPEG_QUALITY.id(): jpegOptions['quality'],
                    JESettingsKey.CONFIG_JPEG_SMOOTHING.id(): jpegOptions['smoothing'],
                    JESettingsKey.CONFIG_JPEG_SUBSAMPLING.id(): jpegOptions['subsampling'],
                    JESettingsKey.CONFIG_JPEG_PROGRESSIVE.id(): jpegOptions['progressive'],
                    JESettingsKey.CONFIG_JPEG_OPTIMIZE.id(): jpegOptions['optimize'],
                    JESettingsKey.CONFIG_JPEG_SAVEPROFILE.id(): jpegOptions['saveProfile'],
                    JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR.id(): jpegOptions['transparencyFillcolor'],
                    JESettingsKey.CONFIG_RENDER_MODE.id(): JESettingsValues.RENDER_MODE_FINAL,
                    JESettingsKey.CONFIG_MISC_CROP_ACTIVE.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_CROP_ACTIVE),
                    JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE),
                    JESettingsKey.CONFIG_MISC_RESIZE_UNIT.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_UNIT),
                    JESettingsKey.CONFIG_MISC_RESIZE_FILTER.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_FILTER),
                    JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE),
                    JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH),
                    JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT.id(): self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT)
                    }

        if self.rbRenderNormal.isChecked():
            returned[JESettingsKey.CONFIG_RENDER_MODE.id()] = JESettingsValues.RENDER_MODE_FINAL
        elif self.rbRenderDifference.isChecked():
            returned[JESettingsKey.CONFIG_RENDER_MODE.id()] = JESettingsValues.RENDER_MODE_DIFFVALUE
        elif self.rbRenderXOR.isChecked():
            returned[JESettingsKey.CONFIG_RENDER_MODE.id()] = JESettingsValues.RENDER_MODE_DIFFBITS
        elif self.rbRenderSrc.isChecked():
            returned[JESettingsKey.CONFIG_RENDER_MODE.id()] = JESettingsValues.RENDER_MODE_SOURCE

        return returned

    def __calculateBounds(self):
        """calculate bounds from source document
        . document if cropped to selection
        . selection  if not cropped to selection
        """
        selection = self.__doc.selection()
        self.wContentOptions.setDocSelection(selection)
        self.__boundsSource = None

        if self.wContentOptions.hasDocSelection() and self.wContentOptions.property(JESettingsKey.CONFIG_MISC_CROP_ACTIVE) and selection:
            self.__boundsSource = QRect(selection.x(),
                                        selection.y(),
                                        selection.width(),
                                        selection.height()
                                        ).intersected(QRect(0, 0, self.__doc.width(), self.__doc.height()))
            if self.__boundsSource.width() == 0 or self.__boundsSource.height() == 0:
                self.__boundsSource = None

        if self.__boundsSource is None:
            self.__boundsSource = QRect(0, 0, self.__doc.width(), self.__doc.height())

        self.__updateNewSize(False, True)

    def __updateNewSize(self, immediate=False, recalculateOnly=False):
        """Size (width and/or height) has been changed

        Trigger an __updateDoc after few milliseconds
        The delay let the possibility to user to change height (after width has been modified, for example) before resizing process is applied
        """
        self.__updatePosition()

        if self.__timerResize != 0:
            self.killTimer(self.__timerResize)
            self.__timerResize = 0

        if self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE):
            currentUnit = self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_UNIT)

            # resize checked, recalculate target size
            if currentUnit == JESettingsValues.UNIT_PX:
                # pixels
                self.__sizeTarget = imgBoxSize(self.__boundsSource.size(),
                                               QSize(self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH),
                                                     self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT)
                                                     )
                                               )
            elif currentUnit == JESettingsValues.UNIT_PCT:
                # pct
                pctValue = self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE) / 100
                self.__sizeTarget = QSize(round(self.__boundsSource.width() * pctValue),
                                          round(self.__boundsSource.height() * pctValue))
            elif currentUnit == JESettingsValues.UNIT_PX_WIDTH:
                # pixels
                self.__sizeTarget = imgBoxSize(self.__boundsSource.size(),
                                               QSize(self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH),
                                                     JEMainWindow.__MAX_WIDTH_AND_HEIGHT
                                                     )
                                               )
            elif currentUnit == JESettingsValues.UNIT_PX_HEIGHT:
                # pixels
                self.__sizeTarget = imgBoxSize(self.__boundsSource.size(),
                                               QSize(JEMainWindow.__MAX_WIDTH_AND_HEIGHT,
                                                     self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT)
                                                     )
                                               )
        else:
            # resize not checked, target size = source size
            self.__sizeTarget = QSize(self.__boundsSource.size())

        if not recalculateOnly:
            if immediate:
                self.__updateDoc(JEMainWindow.__UPDATE_MODE_RESIZE)
            else:
                self.__timerResize = self.startTimer(JEMainWindow.__RESIZE_DELAY)

    def __updatePosition(self):
        """Get current slider position"""
        if not self.__viewScrollbarH:
            # can occurs during initialisation phase
            return

        if self.wContentOptions.hasDocSelection() and self.wContentOptions.property(JESettingsKey.CONFIG_MISC_CROP_ACTIVE):
            # crop mode
            self.__positionCrop = QPoint(self.__viewScrollbarH.sliderPosition(), self.__viewScrollbarV.sliderPosition())
        else:
            # full mode
            self.__positionFull = QPoint(self.__viewScrollbarH.sliderPosition(), self.__viewScrollbarV.sliderPosition())

    def __updateDoc(self, mode=None):
        """Update temporary document, taking in account the current checkbox 'Crop to selection' & 'Resize document' state"""
        self.wsmSetups.setCurrentSetupData(self.__setupData())

        # recalculate bounds
        self.__calculateBounds()

        applyResize = (self.__sizeTarget != self.__boundsSource.size())

        if not applyResize and mode == JEMainWindow.__UPDATE_MODE_RESIZE and self.__sizeTarget == self.__tmpDoc.bounds().size():
            return

        # update internal document
        self.__tmpDoc.crop(0, 0, self.__boundsSource.width(), self.__boundsSource.height())
        self.__tmpDocTgtNode.setPixelData(self.__doc.pixelData(self.__boundsSource.x(),
                                                               self.__boundsSource.y(),
                                                               self.__boundsSource.width(),
                                                               self.__boundsSource.height()),
                                          0, 0, self.__boundsSource.width(), self.__boundsSource.height())
        if applyResize:
            resolution = round(self.__tmpDoc.xRes())
            self.__tmpDoc.scaleImage(self.__sizeTarget.width(), self.__sizeTarget.height(), resolution, resolution, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_FILTER))
        self.__tmpDoc.refreshProjection()

        # force jpeg export from tmpDoc => update preview
        self.timerEvent(None)

        self.__tmpDocPreview.crop(0, 0, self.__tmpDoc.width(), self.__tmpDoc.height())
        self.__tmpDocPreviewSrcNode.setPixelData(self.__tmpDoc.pixelData(0, 0, self.__tmpDoc.width(), self.__tmpDoc.height()), 0, 0, self.__tmpDoc.width(), self.__tmpDoc.height())
        self.__tmpDocPreview.refreshProjection()

        if self.wContentOptions.hasDocSelection() and self.wContentOptions.property(JESettingsKey.CONFIG_MISC_CROP_ACTIVE):
            # crop mode
            if self.__positionCrop is None:
                # no position in memory, center
                for scrollbar in [self.__viewScrollbarH, self.__viewScrollbarV]:
                    newPosition = scrollbar.minimum()+(scrollbar.maximum() - scrollbar.minimum())//2
                    scrollbar.setSliderPosition(newPosition)
            else:
                # last position memorized, restore
                self.__viewScrollbarH.setSliderPosition(self.__positionCrop.x())
                self.__viewScrollbarV.setSliderPosition(self.__positionCrop.y())
        else:
            # last position memorized, restore
            self.__viewScrollbarH.setSliderPosition(self.__positionFull.x())
            self.__viewScrollbarV.setSliderPosition(self.__positionFull.y())

        self.lblDocDimension.setText(i18n(f"Dimensions: {self.__tmpDoc.width()}x{self.__tmpDoc.height()}"))

    def __saveFileName(self):
        """Set exported file name"""
        fDialog = WEFileDialog()
        fDialog.setFileMode(QFileDialog.AnyFile)
        fDialog.setNameFilter(i18n("JPEG image (*.jpg *.jpeg)"))
        fDialog.setViewMode(QFileDialog.Detail)
        fDialog.setAcceptMode(QFileDialog.AcceptSave)
        fDialog.setDefaultSuffix('jpeg')
        fDialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

        if self.leFileName.text() != '':
            fDialog.selectFile(self.leFileName.text())
        else:
            fDialog.setDirectory(JESettings.get(JESettingsKey.CONFIG_FILE_LASTPATH))

        if fDialog.exec():
            self.leFileName.setText(fDialog.file())
            self.pbOk.setEnabled(True)

    def __renderModeChanged(self):
        """Render mode has been changed, update blending mode"""
        if self.rbRenderNormal.isChecked():
            self.__tmpDocPreviewFileNode.setBlendingMode('normal')
            self.__tmpDocPreviewFileNode.setVisible(True)
        elif self.rbRenderDifference.isChecked():
            self.__tmpDocPreviewFileNode.setBlendingMode('divisive_modulo_continuous')
            self.__tmpDocPreviewFileNode.setVisible(True)
        elif self.rbRenderXOR.isChecked():
            self.__tmpDocPreviewFileNode.setBlendingMode('xor')
            self.__tmpDocPreviewFileNode.setVisible(True)
        elif self.rbRenderSrc.isChecked():
            self.__tmpDocPreviewFileNode.setBlendingMode('normal')
            self.__tmpDocPreviewFileNode.setVisible(False)

    def __updatePreview(self, src=None):
        """Update preview, according to current jpeg export settings"""
        if self.__timerPreview != 0:
            # if a timer is already running, kill it
            self.killTimer(self.__timerPreview)
        # create a new timer, waiting a little bit before rendering preview
        # (avoid to render preview each time a property is modified)
        self.__timerPreview = self.startTimer(JEMainWindow.__UPDATE_DELAY)
        self.wsmSetups.setCurrentSetupData(self.__setupData())

    def timerEvent(self, event):
        """Update preview when timer is triggered"""
        if event is None or event.timerId() == self.__timerPreview:
            # it's a timer preview; refresh preview :-)
            self.killTimer(self.__timerPreview)
            self.__timerPreview = 0

            self.lblEstSize.setText(i18n('Estimated file size: (calculating)'))
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            self.__tmpDoc.exportImage(self.__tmpExportFile, self.wJpegOptions.options(True))

            if self.__tmpDocPreviewFileNode:
                # force file to be reloaded, but it's made asynchronously
                self.__tmpDocPreviewFileNode.resetCache()

                # the waitForDone() does nothing in this case, reset is still made asynchronously....
                self.__tmpDocPreview.waitForDone()
                # ...so the dirty solution: put a one second sleep :-/
                # it doesn't fix the problem (1250ms could be too long or too short, according to computer and image size)
                # but that's better than nothing
                Timer.sleep(1250)

            try:
                size = os.path.getsize(self.__tmpExportFile)
                self.lblEstSize.setText(i18n(f'Estimated file size: {bytesSizeToStr(size)}'))
            except Exception as e:
                self.lblEstSize.setText(i18n('Estimated file size: unable to calculate'))

            QApplication.restoreOverrideCursor()
        elif event.timerId() == self.__timerResize:
            # it's a timer resize; update resize
            self.killTimer(self.__timerResize)
            self.__timerResize = 0
            self.__updateDoc(JEMainWindow.__UPDATE_MODE_RESIZE)

    def __imageClosed(self, docName):
        """A view has been closed; check if it's one of view used for documents"""
        if docName == self.__tmpExportPreviewFile:
            # preview has been closed: cancel current JPEG Export
            # has file has been closed, pointer to document and file layer are not
            # valid anymore, must define pointer to None
            self.__tmpDocPreview = None
            self.__tmpDocPreviewFileNode = None
            self.__closeDocPreview(True)
            self.__rejectChange()
        elif docName == self.__docFileName:
            # original source document has been closed: cancel current JPEG Export
            self.__closeDocPreview(True)
            self.__rejectChange()

    def __rejectChange(self):
        """User clicked on cancel button"""
        # need save last setups file name in all case
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_LASTFILE, self.wsmSetups.lastFileName())
        JESettings.save()
        self.wsmSetups.saveSetup(self.wsmSetups.lastFileName())

        self.close()

    def __acceptChange(self):
        """User clicked on OK button"""
        # do export
        self.__accepted = True

        # save export preferences
        options = self.wJpegOptions.options()

        rect = self.geometry()

        JESettings.set(JESettingsKey.CONFIG_FILE_LASTPATH, os.path.dirname(self.leFileName.text()))

        JESettings.set(JESettingsKey.CONFIG_WINDOW_GEOMETRY_SIZE_WIDTH, rect.width())
        JESettings.set(JESettingsKey.CONFIG_WINDOW_GEOMETRY_SIZE_HEIGHT, rect.height())
        JESettings.set(JESettingsKey.CONFIG_WINDOW_GEOMETRY_POSITION_X, rect.x())
        JESettings.set(JESettingsKey.CONFIG_WINDOW_GEOMETRY_POSITION_Y, rect.y())

        JESettings.set(JESettingsKey.CONFIG_JPEG_QUALITY, options['quality'])
        JESettings.set(JESettingsKey.CONFIG_JPEG_SMOOTHING, options['smoothing'])
        JESettings.set(JESettingsKey.CONFIG_JPEG_SUBSAMPLING, options['subsampling'])
        JESettings.set(JESettingsKey.CONFIG_JPEG_PROGRESSIVE, options['progressive'])
        JESettings.set(JESettingsKey.CONFIG_JPEG_OPTIMIZE, options['optimize'])
        JESettings.set(JESettingsKey.CONFIG_JPEG_SAVEPROFILE, options['saveProfile'])
        JESettings.set(JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR, options['transparencyFillcolor'].name())

        if self.rbRenderNormal.isChecked():
            JESettings.set(JESettingsKey.CONFIG_RENDER_MODE, JESettingsValues.RENDER_MODE_FINAL)
        elif self.rbRenderDifference.isChecked():
            JESettings.set(JESettingsKey.CONFIG_RENDER_MODE, JESettingsValues.RENDER_MODE_DIFFVALUE)
        elif self.rbRenderXOR.isChecked():
            JESettings.set(JESettingsKey.CONFIG_RENDER_MODE, JESettingsValues.RENDER_MODE_DIFFBITS)
        elif self.rbRenderSrc.isChecked():
            JESettings.set(JESettingsKey.CONFIG_RENDER_MODE, JESettingsValues.RENDER_MODE_SOURCE)

        JESettings.set(JESettingsKey.CONFIG_MISC_CROP_ACTIVE, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_CROP_ACTIVE))
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE))

        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_UNIT, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_UNIT))
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_FILTER, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_FILTER))
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE))
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH))
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT, self.wContentOptions.property(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT))

        JESettings.setTxtColorPickerLayout(self.wsmSetups.propertiesEditorColorPickerLayout())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_LASTFILE, self.wsmSetups.lastFileName())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_ZOOMLEVEL, self.wsmSetups.iconSizeIndex())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLUMNWIDTH, self.wsmSetups.columnSetupWidth())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_VIEWMODE, self.wsmSetups.propertiesEditorIconSelectorViewMode())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_ZOOMLEVEL, self.wsmSetups.propertiesEditorIconSelectorIconSizeIndex())

        JESettings.save()

        self.wsmSetups.saveSetup(self.wsmSetups.lastFileName())

        self.close()

    def __displayAbout(self):
        # display about window
        WAboutWindow(self.__jeName, self.__jeVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':JPEG Export')

    def __closeDocPreview(self, deleteTmpFile=False):
        """Close the temporary document preview"""
        if self.__tmpDocPreview:
            # note:
            #   closing a document that has been modified and added into a view seems
            #   to ask user confirmation yes/no/cancel
            #   that's a problem here, and batch mode doesn't change anything
            #   the dirty trick is to save document in a temp file, close document,
            #   and finally delete temp file
            self.__tmpDocPreview.save()
            self.__tmpDocPreview.waitForDone()
            self.__tmpDocPreview.close()
            self.__tmpDocPreview = None

        if os.path.isfile(self.__tmpExportPreviewFile):
            os.remove(self.__tmpExportPreviewFile)

        if deleteTmpFile and os.path.isfile(self.__tmpExportFile):
            os.remove(self.__tmpExportFile)

    def __closeTempView(self):
        if self.__timerPreview != 0:
            self.killTimer(self.__timerPreview)

        self.__closeDocPreview(False)

        if self.__tmpDoc:
            self.__tmpDoc.close()
            self.__tmpDoc.waitForDone()
            self.__tmpDoc = None

        if os.path.isfile(self.__tmpExportFile):
            if self.__accepted:
                try:
                    shutil.move(self.__tmpExportFile, self.leFileName.text())
                    self.__tmpExportFile = None
                except Exception as e:
                    QMessageBox.warning(QWidget(), i18n("JPEG export"), i18n(f"Unable to export file to {self.leFileName.text()}"))
                    os.remove(self.__tmpExportFile)
                    print(e)
            else:
                os.remove(self.__tmpExportFile)

    def closeEvent(self, event):
        """Window is closed"""
        if not self.__notifier:
            # exit in init phase, before anything was initialized
            return

        try:
            self.__notifier.imageClosed.disconnect(self.__imageClosed)
        except Exception:
            pass
        self.__closeTempView()
        JEMainWindow.__IS_OPENED = False
