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
import os.path
import re
import shutil
from krita import Krita

import PyQt5.uic

from PyQt5.QtCore import QDir
from PyQt5.Qt import *
from PyQt5.QtWidgets import (
        QDialog,
        QWidget
    )

from .jesettings import (
        JESettings,
        JESettingsKey,
        JESettingsValues
    )

from jpegexport.pktk.modules.about import AboutWindow
from jpegexport.pktk.modules.edialog import EDialog
from jpegexport.pktk.modules.strutils import bytesSizeToStr
from jpegexport.pktk.modules.imgutils import imgBoxSize
from jpegexport.pktk.modules.timeutils import Timer
from jpegexport.pktk.widgets.wefiledialog import WEFileDialog

from jpegexport.pktk.modules.ekrita import (
        EKritaWindow,
        EKritaDocument,
        EKritaNode
    )



# -----------------------------------------------------------------------------
class JEMainWindow(EDialog):
    """Main JpegExport window"""

    # A flag to ensure that class is instancied only once
    __IS_OPENED=False

    # delay between modified properties and preview update
    __UPDATE_DELAY=375
    __RESIZE_DELAY=625

    __UPDATE_MODE_CROP=   0b00000001
    __UPDATE_MODE_RESIZE= 0b00000010

    __RESIZE_METHOD=[
            (i18n('B-Spline'),          JESettingsValues.FILTER_BSPLINE),
            ('Bell',                    JESettingsValues.FILTER_BELL),
            (i18n('Bicubic'),           JESettingsValues.FILTER_BICUBIC),
            (i18n('Bilinear'),          JESettingsValues.FILTER_BILINEAR),
            ('Hermite',                 JESettingsValues.FILTER_HERMITE),
            (i18n('Lancsoz3'),          JESettingsValues.FILTER_LANCZOS3),
            ('Mitchell',                JESettingsValues.FILTER_MITCHELL),
            (i18n('Nearest neighbour'), JESettingsValues.FILTER_NEAREST_NEIGHBOUR)
        ]


    def __init__(self, jeName="JPEG Export", jeVersion="testing", parent=None):
        super(JEMainWindow, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'jemainwindow.ui'), parent)

        self.__notifier = None

        # another instance already exist, exit
        if JEMainWindow.__IS_OPENED:
            self.close()
            return

        self.__accepted=False

        self.__timerPreview=0                   # timer used for preview update
        self.__timerResize=0                    # timer used for resize update

        self.__tmpDoc=None                      # internal document used for export (not added to view)
        self.__tmpDocTgtNode=None
        self.__tmpDocPreview=None               # document used for preview (added to view)
        self.__tmpDocPreviewFileNode=None
        self.__tmpDocPreviewSrcNode=None

        self.__jeName = jeName
        self.__jeVersion = jeVersion

        self.__viewScrollbarH=None
        self.__viewScrollbarV=None
        self.__positionFull=None
        self.__positionCrop=None

        self.__doc=Krita.instance().activeDocument()
        self.__boundsSource=None
        self.__sizeTarget=None

        if self.__doc is None:
            # no document opened: cancel plugin
            QMessageBox.warning(
                    QWidget(),
                    f"{jeName}",
                    i18n("There's no active document: <i>JPEG Export</i> plugin only works with opened documents")
                )
            self.close()
            return

        JEMainWindow.__IS_OPENED=True

        basename, ext=os.path.splitext(os.path.basename(self.__doc.fileName()))
        self.__tmpExportPreviewFile=os.path.join(QDir.tempPath(), f'{basename} (JPEG Export Preview).jpeg')
        self.__tmpExportFile=os.path.join(QDir.tempPath(), f'jpegexport-{QUuid.createUuid().toString(QUuid.Id128)}.jpeg')
        self.__docFileName=self.__doc.fileName()

        self.__notifier=Krita.instance().notifier()
        self.__notifier.imageClosed.connect(self.__imageClosed)

        self.setModal(False)
        self.setWindowTitle(i18n(f'{jeName} v{jeVersion}'))
        self.setWindowFlags(Qt.Dialog|Qt.WindowTitleHint|Qt.WindowStaysOnTopHint)

        self.__initialiseUi()
        self.__initialiseDoc()

        self.show()


    def showEvent(self, event):
        """Dialog is visible"""
        # define minimum width for pct input value, according to current width defined for width/height input values
        self.dsbResizePct.setMinimumWidth(self.sbResizedMaxWidth.width()+self.sbResizedMaxHeight.width()+self.lblResizeX.width())
        self.dsbResizePct.setMaximumWidth(self.sbResizedMaxWidth.width()+self.sbResizedMaxHeight.width()+self.lblResizeX.width())
        self.__updateResizeUnit(False)


    def __initialiseDoc(self):
        """Initialise temporary document"""
        self.__calculateBounds()

        # The __tmpDoc contain a flatened copy of current document
        self.__tmpDoc=Krita.instance().createDocument(self.__boundsSource.width(), self.__boundsSource.height(), "Jpeg Export - Temporary preview", self.__doc.colorModel(), self.__doc.colorDepth(), self.__doc.colorProfile(), self.__doc.resolution())
        self.__tmpDocTgtNode=self.__tmpDoc.createNode("Preview", "paintlayer")
        #self.__tmpDocTgtNode.setPixelData(self.__doc.pixelData(self.__boundsSource.x(), self.__boundsSource.y(), self.__boundsSource.width(), self.__boundsSource.height()), 0, 0, self.__boundsSource.width(), self.__boundsSource.height() )
        self.__tmpDoc.rootNode().addChildNode(self.__tmpDocTgtNode, None)
        self.__tmpDoc.setBatchmode(True)
        # force jpeg export
        self.timerEvent(None)

        # The __tmpDocPreview contain the Jpeg file for preview
        self.__tmpDocPreview=Krita.instance().createDocument(self.__boundsSource.width(), self.__boundsSource.height(), "Jpeg Export - Temporary preview", self.__doc.colorModel(), self.__doc.colorDepth(), self.__doc.colorProfile(), self.__doc.resolution())
        # add original document content, as reference for diff
        self.__tmpDocPreviewSrcNode=self.__tmpDocPreview.createNode("Source", "paintlayer")
        #self.__tmpDocPreviewSrcNode.setPixelData(self.__doc.pixelData(self.__boundsSource.x(), self.__boundsSource.y(), self.__boundsSource.width(), self.__boundsSource.height()), 0, 0, self.__boundsSource.width(), self.__boundsSource.height() )
        self.__tmpDocPreview.rootNode().addChildNode(self.__tmpDocPreviewSrcNode, None)
        # add file layer linked to exported jpeg document, to see preview
        self.__tmpDocPreviewFileNode=self.__tmpDocPreview.createFileLayer("Preview", self.__tmpExportFile, "None")
        self.__tmpDocPreview.rootNode().addChildNode(self.__tmpDocPreviewFileNode, None)
        self.__tmpDocPreview.setBatchmode(True)
        self.__tmpDocPreview.setFileName(self.__tmpExportPreviewFile)


        Krita.instance().activeWindow().addView(self.__tmpDocPreview) # shows it in the application

        #self.lblDocDimension.setText(i18n(f"Dimensions: {self.__tmpDoc.width()}x{self.__tmpDoc.height()}"))

        scrollbars=EKritaWindow.scrollbars()
        if scrollbars:
            self.__viewScrollbarH, self.__viewScrollbarV=scrollbars
            self.__viewScrollbarH.sliderMoved.connect(self.__updatePosition)
            self.__viewScrollbarV.sliderMoved.connect(self.__updatePosition)
            self.__updatePosition()

        self.__updateDoc()
        self.__renderModeChanged()


    def __initialiseUi(self):
        """Initialise window interface"""
        JESettings.load()

        self.wJpegOptions.setOptions({
                'quality': JESettings.get(JESettingsKey.CONFIG_JPEG_QUALITY),
                'smoothing': JESettings.get(JESettingsKey.CONFIG_JPEG_SMOOTHING),
                'subsampling': JESettings.get(JESettingsKey.CONFIG_JPEG_SUBSAMPLING),
                'progressive': JESettings.get(JESettingsKey.CONFIG_JPEG_PROGRESSIVE),
                'optimize': JESettings.get(JESettingsKey.CONFIG_JPEG_OPTIMIZE),
                'saveProfile': JESettings.get(JESettingsKey.CONFIG_JPEG_SAVEPROFILE),
                'transparencyFillcolor': JESettings.get(JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR)
            })

        newFileName=self.__doc.fileName()
        if newFileName=='':
            newFileName=os.path.join(JESettings.get(JESettingsKey.CONFIG_FILE_LASTPATH), 'newDocument.jpeg')
        else:
            newFileName=re.sub('\.[^.]+$', '.jpeg', newFileName)

        self.leFileName.setText(newFileName)

        renderMode=JESettings.get(JESettingsKey.CONFIG_RENDER_MODE)
        if renderMode==JESettingsValues.RENDER_MODE_FINAL:
            self.rbRenderNormal.setChecked(True)
        elif renderMode==JESettingsValues.RENDER_MODE_DIFFVALUE:
            self.rbRenderDifference.setChecked(True)
        elif renderMode==JESettingsValues.RENDER_MODE_DIFFBITS:
            self.rbRenderXOR.setChecked(True)
        elif renderMode==JESettingsValues.RENDER_MODE_SOURCE:
            self.rbRenderSrc.setChecked(True)

        self.wJpegOptions.optionUpdated.connect(self.__updatePreview)
        self.pbOk.clicked.connect(self.__acceptChange)
        self.pbCancel.clicked.connect(self.__rejectChange)
        self.pbAbout.clicked.connect(self.__displayAbout)

        self.rbRenderNormal.toggled.connect(self.__renderModeChanged)
        self.rbRenderDifference.toggled.connect(self.__renderModeChanged)
        self.rbRenderXOR.toggled.connect(self.__renderModeChanged)
        self.rbRenderSrc.toggled.connect(self.__renderModeChanged)


        # crop
        self.cbCropToSelection.setChecked(JESettings.get(JESettingsKey.CONFIG_MISC_CROP_ACTIVE))
        selection=self.__doc.selection()
        if selection:
            self.cbCropToSelection.setEnabled(True)
            self.cbCropToSelection.setText(i18n("Crop to selection")+f" ({selection.width()}x{selection.height()})")
        else:
            self.cbCropToSelection.setEnabled(False)

        # resize
        self.cbResizeDocument.setChecked(JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE))

        self.cbxResizedUnit.addItem('px')
        self.cbxResizedUnit.addItem('%')
        self.cbxResizedUnit.setCurrentText(JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_UNIT))


        defaultSelected=JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_FILTER)
        for index, value in enumerate(JEMainWindow.__RESIZE_METHOD):
            self.cbxResizeFilter.addItem(value[0], value[1])
            if value[1]==defaultSelected:
                self.cbxResizeFilter.setCurrentIndex(index)

        self.dsbResizePct.setValue(JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE))
        self.sbResizedMaxWidth.setValue(JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH))
        self.sbResizedMaxHeight.setValue(JESettings.get(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT))
        self.wResizeOptions.setEnabled(self.cbResizeDocument.isChecked())

        # signals
        self.cbCropToSelection.toggled.connect(lambda x: self.__updateDoc(JEMainWindow.__UPDATE_MODE_CROP))
        self.cbResizeDocument.toggled.connect(lambda x: self.__updateNewSize(True))
        self.cbxResizedUnit.currentIndexChanged.connect(lambda x: self.__updateResizeUnit(True))
        self.cbxResizeFilter.currentIndexChanged.connect(lambda x: self.__updateNewSize(False))
        self.sbResizedMaxWidth.valueChanged.connect(lambda x: self.__updateNewSize(False))
        self.sbResizedMaxHeight.valueChanged.connect(lambda x: self.__updateNewSize(False))
        self.dsbResizePct.valueChanged.connect(lambda x: self.__updateNewSize(False))

        self.tbSaveAs.clicked.connect(self.__saveFileName)
        self.leFileName.mouseDoubleClickEvent=lambda x: self.__saveFileName()


    def __updatePosition(self):
        """Get current slider position"""
        if not self.__viewScrollbarH:
            # can occurs during initialisation phase
            return

        if self.cbCropToSelection.isEnabled() and self.cbCropToSelection.isChecked():
            # crop mode
            self.__positionCrop=QPoint(self.__viewScrollbarH.sliderPosition(), self.__viewScrollbarV.sliderPosition())
        else:
            # full mode
            self.__positionFull=QPoint(self.__viewScrollbarH.sliderPosition(), self.__viewScrollbarV.sliderPosition())


    def __calculateBounds(self):
        """calculate bounds from source document
        . document if cropped to selection
        . selection  if not cropped to selection
        """
        selection=self.__doc.selection()
        self.__boundsSource=None

        if self.cbCropToSelection.isEnabled() and self.cbCropToSelection.isChecked() and selection:
            self.__boundsSource=QRect(selection.x(), selection.y(), selection.width(), selection.height()).intersected(QRect(0, 0, self.__doc.width(), self.__doc.height()))
            if self.__boundsSource.width()==0 or self.__boundsSource.height()==0:
                self.__boundsSource=None
                self.cbCropToSelection.setEnabled(False)

        if self.__boundsSource is None:
            self.__boundsSource=QRect(0, 0, self.__doc.width(), self.__doc.height())

        self.__updateNewSize(False, True)


    def __updateResizeUnit(self, updateSize=True):
        """Unit has been modified (px, %)

        Update width/height according to unit
        """
        if self.cbxResizedUnit.currentIndex()==0:
            # from % to px
            self.dsbResizePct.setVisible(False)
            self.sbResizedMaxWidth.setVisible(True)
            self.lblResizeX.setVisible(True)
            self.sbResizedMaxHeight.setVisible(True)
        else:
            # from px to %
            self.sbResizedMaxWidth.setVisible(False)
            self.lblResizeX.setVisible(False)
            self.sbResizedMaxHeight.setVisible(False)
            self.dsbResizePct.setVisible(True)

        if updateSize:
            self.__updateNewSize(True, False)


    def __updateNewSize(self, immediate=False, recalculateOnly=False):
        """Size (width and/or height) has been changed

        Trigger an __updateDoc after few milliseconds
        The delay let the possibility to user to change height (after width has been modified, for example) before resizing process is applied
        """
        self.__updatePosition()

        if self.__timerResize!=0:
            self.killTimer(self.__timerResize)
            self.__timerResize=0

        if self.cbResizeDocument.isChecked():
            # resize checked, recalculate target size
            if self.cbxResizedUnit.currentIndex()==0:
                # pixels
                self.__sizeTarget=imgBoxSize(self.__boundsSource.size(), QSize(self.sbResizedMaxWidth.value(), self.sbResizedMaxHeight.value()))
            else:
                # pct
                self.__sizeTarget=QSize(round(self.__boundsSource.width() * self.dsbResizePct.value() / 100), round(self.__boundsSource.height() * self.dsbResizePct.value() / 100))
        else:
            # resize not checked, target size=source size
            self.__sizeTarget=QSize(self.__boundsSource.size())

        if not recalculateOnly:
            if immediate:
                self.__updateDoc(JEMainWindow.__UPDATE_MODE_RESIZE)
            else:
                self.__timerResize=self.startTimer(JEMainWindow.__RESIZE_DELAY)


    def __updateDoc(self, mode=None):
        """Update temporary document, taking in account the current checkbox 'Crop to selection' & 'Resize document' state"""
        # recalculate bounds
        self.__calculateBounds()

        self.wResizeOptions.setEnabled(self.cbResizeDocument.isChecked())
        applyResize=(self.__sizeTarget!=self.__boundsSource.size())

        if not applyResize and mode==JEMainWindow.__UPDATE_MODE_RESIZE and self.__sizeTarget==self.__tmpDoc.bounds().size():
            return

        # update internal document
        self.__tmpDoc.crop(0, 0, self.__boundsSource.width(), self.__boundsSource.height())
        self.__tmpDocTgtNode.setPixelData(self.__doc.pixelData(self.__boundsSource.x(), self.__boundsSource.y(), self.__boundsSource.width(), self.__boundsSource.height()), 0, 0, self.__boundsSource.width(), self.__boundsSource.height())
        if applyResize:
            resolution=self.__tmpDoc.xRes()
            self.__tmpDoc.scaleImage(self.__sizeTarget.width(), self.__sizeTarget.height(), resolution, resolution, self.cbxResizeFilter.currentData())
        self.__tmpDoc.refreshProjection()

        # force jpeg export from tmpDoc=>update preview
        self.timerEvent(None)

        self.__tmpDocPreview.crop(0, 0, self.__tmpDoc.width(), self.__tmpDoc.height())
        self.__tmpDocPreviewSrcNode.setPixelData(self.__tmpDoc.pixelData(0, 0, self.__tmpDoc.width(), self.__tmpDoc.height()), 0, 0, self.__tmpDoc.width(), self.__tmpDoc.height())
        self.__tmpDocPreview.refreshProjection()

        if self.cbCropToSelection.isEnabled() and self.cbCropToSelection.isChecked():
            # crop mode
            if self.__positionCrop is None:
                # no position in memory, center
                for scrollbar in [self.__viewScrollbarH, self.__viewScrollbarV]:
                    newPosition=scrollbar.minimum()+(scrollbar.maximum() - scrollbar.minimum())//2
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
        fDialog=WEFileDialog()
        fDialog.setFileMode(QFileDialog.AnyFile)
        fDialog.setNameFilter(i18n("JPEG image (*.jpg *.jpeg)"))
        fDialog.setViewMode(QFileDialog.Detail)
        fDialog.setAcceptMode(QFileDialog.AcceptSave)
        fDialog.setDefaultSuffix('jpeg')

        if self.leFileName.text()!='':
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


    def __updatePreview(self):
        """Update preview, according to current jpeg export settings"""
        if self.__timerPreview!=0:
            # if a timer is already running, kill it
            self.killTimer(self.__timerPreview)
        # create a new timer, waiting a little bit before rendering preview
        # (avoid to render preview each time a property is modified)
        self.__timerPreview=self.startTimer(JEMainWindow.__UPDATE_DELAY)


    def timerEvent(self, event):
        """Update preview when timer is triggered"""
        if event is None or event.timerId()==self.__timerPreview:
            # it's a timer preview; refresh preview :-)
            self.killTimer(self.__timerPreview)
            self.__timerPreview=0

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
                size=os.path.getsize(self.__tmpExportFile)
                self.lblEstSize.setText(i18n(f'Estimated file size: {bytesSizeToStr(size)}'))
            except Exception as e:
                self.lblEstSize.setText(i18n('Estimated file size: unable to calculate'))

            QApplication.restoreOverrideCursor()
        elif event.timerId()==self.__timerResize:
            # it's a timer resize; update resize
            self.killTimer(self.__timerResize)
            self.__timerResize=0
            self.__updateDoc(JEMainWindow.__UPDATE_MODE_RESIZE)


    def __imageClosed(self, docName):
        """A view has been closed; check if it's one of view used for documents"""
        if docName==self.__tmpExportPreviewFile:
            # preview has been closed: cancel current JPEG Export
            self.__tmpDocPreview=None
            self.__rejectChange()
        elif docName==self.__docFileName:
            # original soruce document has been closed: cancel current JPEG Export
            self.__rejectChange()


    def __rejectChange(self):
        """User clicked on cancel button"""
        self.close()


    def __acceptChange(self):
        """User clicked on OK button"""
        # do export
        self.__accepted=True

        # save export preferences
        options=self.wJpegOptions.options()

        JESettings.set(JESettingsKey.CONFIG_FILE_LASTPATH, os.path.dirname(self.leFileName.text()))

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


        JESettings.set(JESettingsKey.CONFIG_MISC_CROP_ACTIVE, self.cbCropToSelection.isChecked())
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE, self.cbResizeDocument.isChecked())

        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_UNIT, self.cbxResizedUnit.currentText())
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_FILTER, self.cbxResizeFilter.currentData())
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE, self.dsbResizePct.value())
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH, self.sbResizedMaxWidth.value())
        JESettings.set(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT, self.sbResizedMaxHeight.value())

        JESettings.save()

        self.close()


    def __displayAbout(self):
        # display about window
        AboutWindow(self.__jeName, self.__jeVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':JPEG Export')


    def __closeTempView(self):
        if self.__timerPreview!=0:
            self.killTimer(self.__timerPreview)

        if self.__tmpDocPreview:
            # note:
            #   closing a document that has been modified and added into a view seems
            #   to ask user confirmation yes/no/cancel
            #   that's a problem here, and batch mode doesn't change anything
            #   the dirty trick is to save document in a temp file, close document,
            #   and finally delete temp file
            self.__tmpDocPreview.save()
            self.__tmpDocPreview.waitForDone()
            self.__tmpDocPreview.close()
            self.__tmpDocPreview.waitForDone()
            self.__tmpDocPreview=None
            self.__tmpDocPreviewFileNode=None

        if self.__tmpDoc:
            self.__tmpDoc.close()
            self.__tmpDoc.waitForDone()
            self.__tmpDoc=None

        if os.path.isfile(self.__tmpExportPreviewFile):
            os.remove(self.__tmpExportPreviewFile)

        if os.path.isfile(self.__tmpExportFile):
            if self.__accepted:
                try:
                    shutil.move(self.__tmpExportFile, self.leFileName.text())
                    self.__tmpExportFile=None
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

        self.__notifier.imageClosed.disconnect(self.__imageClosed)
        self.__closeTempView()
        JEMainWindow.__IS_OPENED=False
