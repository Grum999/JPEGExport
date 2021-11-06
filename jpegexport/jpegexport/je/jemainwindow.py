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

    def __init__(self, jeName="JPEG Export", jeVersion="testing", parent=None):
        super(JEMainWindow, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'jemainwindow.ui'), parent)

        self.__notifier = None

        # another instance already exist, exit
        if JEMainWindow.__IS_OPENED:
            self.close()
            return

        self.__accepted=False

        self.__timer=0
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
        self.__bounds=None

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


    def __initialiseDoc(self):
        """Initialise temporary document"""
        self.__calculateBounds()

        # The __tmpDoc contain a flatened copy of current document
        self.__tmpDoc=Krita.instance().createDocument(self.__bounds.width(), self.__bounds.height(), "Jpeg Export - Temporary preview", self.__doc.colorModel(), self.__doc.colorDepth(), self.__doc.colorProfile(), self.__doc.resolution())
        self.__tmpDocTgtNode=self.__tmpDoc.createNode("Preview", "paintlayer")
        self.__tmpDocTgtNode.setPixelData(self.__doc.pixelData(self.__bounds.x(), self.__bounds.y(), self.__bounds.width(), self.__bounds.height()), 0, 0, self.__bounds.width(), self.__bounds.height() )
        self.__tmpDoc.rootNode().addChildNode(self.__tmpDocTgtNode, None)
        self.__tmpDoc.setBatchmode(True)
        # force jpeg export
        self.timerEvent(None)

        # The __tmpDocPreview contain the Jpeg file for preview
        self.__tmpDocPreview=Krita.instance().createDocument(self.__bounds.width(), self.__bounds.height(), "Jpeg Export - Temporary preview", self.__doc.colorModel(), self.__doc.colorDepth(), self.__doc.colorProfile(), self.__doc.resolution())
        # add original document content, as reference for diff
        self.__tmpDocPreviewSrcNode=self.__tmpDocPreview.createNode("Source", "paintlayer")
        self.__tmpDocPreviewSrcNode.setPixelData(self.__doc.pixelData(self.__bounds.x(), self.__bounds.y(), self.__bounds.width(), self.__bounds.height()), 0, 0, self.__bounds.width(), self.__bounds.height() )
        self.__tmpDocPreview.rootNode().addChildNode(self.__tmpDocPreviewSrcNode, None)
        # add file layer linked to exported jpeg document, to see preview
        self.__tmpDocPreviewFileNode=self.__tmpDocPreview.createFileLayer("Preview", self.__tmpExportFile, "None")
        self.__tmpDocPreview.rootNode().addChildNode(self.__tmpDocPreviewFileNode, None)
        self.__tmpDocPreview.setBatchmode(True)
        self.__tmpDocPreview.setFileName(self.__tmpExportPreviewFile)

        self.__renderModeChanged()

        Krita.instance().activeWindow().addView(self.__tmpDocPreview) # shows it in the application

        scrollbars=EKritaWindow.scrollbars()
        if scrollbars:
            self.__viewScrollbarH, self.__viewScrollbarV=scrollbars
            self.__viewScrollbarH.sliderMoved.connect(self.__updatePosition)
            self.__viewScrollbarV.sliderMoved.connect(self.__updatePosition)
            self.__updatePosition()


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
            newFileName=os.path.join(os.path.normpath(QStandardPaths.writableLocation(QStandardPaths.HomeLocation)), 'newDocument.jpeg')
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

        if self.__doc.selection():
            self.cbCropToSelection.setEnabled(True)
        else:
            self.cbCropToSelection.setEnabled(False)

        self.cbCropToSelection.toggled.connect(self.__updateDoc)

        self.tbSaveAs.clicked.connect(self.__saveFileName)


    def __updatePosition(self):
        """Get current slider position"""
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
        self.__bounds=None

        if self.cbCropToSelection.isEnabled() and self.cbCropToSelection.isChecked() and selection:
            self.__bounds=QRect(selection.x(), selection.y(), selection.width(), selection.height()).intersected(QRect(0, 0, self.__doc.width(), self.__doc.height()))
            if self.__bounds.width()==0 or self.__bounds.height()==0:
                self.__bounds=None
                self.cbCropToSelection.setEnabled(False)

        if self.__bounds is None:
            self.__bounds=QRect(0, 0, self.__doc.width(), self.__doc.height())


    def __updateDoc(self):
        """Update temporary document, taking in account the current checkbox 'Crop to selection' state"""
        # recalculate bounds
        self.__calculateBounds()

        # update internal document
        self.__tmpDoc.setWidth(self.__bounds.width())
        self.__tmpDoc.setHeight(self.__bounds.height())
        self.__tmpDocTgtNode.setPixelData(self.__doc.pixelData(self.__bounds.x(), self.__bounds.y(), self.__bounds.width(), self.__bounds.height()), 0, 0, self.__bounds.width(), self.__bounds.height())
        self.__tmpDoc.refreshProjection()

        # force jpeg export from tmpDoc=>update preview
        self.timerEvent(None)

        self.__tmpDocPreviewSrcNode.setPixelData(self.__doc.pixelData(self.__bounds.x(), self.__bounds.y(), self.__bounds.width(), self.__bounds.height()), 0, 0, self.__bounds.width(), self.__bounds.height())
        self.__tmpDocPreview.setWidth(self.__bounds.width())
        self.__tmpDocPreview.setHeight(self.__bounds.height())
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
            self.__tmpDocPreviewFileNode.setBlendingMode('diff')
            self.__tmpDocPreviewFileNode.setVisible(True)
        elif self.rbRenderXOR.isChecked():
            self.__tmpDocPreviewFileNode.setBlendingMode('xor')
            self.__tmpDocPreviewFileNode.setVisible(True)
        elif self.rbRenderSrc.isChecked():
            self.__tmpDocPreviewFileNode.setBlendingMode('normal')
            self.__tmpDocPreviewFileNode.setVisible(False)


    def __updatePreview(self):
        """Update preview, according to current jpeg export settings"""
        if self.__timer!=0:
            # if a timer is already running, kill it
            self.killTimer(self.__timer)
        # create a new timer, waiting a little bit before rendering preview
        # (avoid to render preview each time a property is modified)
        self.__timer=self.startTimer(JEMainWindow.__UPDATE_DELAY)


    def timerEvent(self, event):
        """Update preview when timer is triggered"""
        self.killTimer(self.__timer)
        self.__timer=0

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

        JESettings.save()

        self.close()


    def __displayAbout(self):
        # display about window
        AboutWindow(self.__jeName, self.__jeVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':JPEG Export')


    def __closeTempView(self):
        if self.__timer!=0:
            self.killTimer(self.__timer)

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
