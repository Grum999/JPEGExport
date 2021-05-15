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

from enum import Enum


import PyQt5.uic
from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal,
        QSettings,
        QStandardPaths
    )

from os.path import join, getsize
import json
import os
import re
import sys
import shutil

from jpegexport.pktk.modules.utils import (
        checkKritaVersion,
        Debug
    )
from jpegexport.pktk.modules.settings import (
                        Settings,
                        SettingsFmt,
                        SettingsKey,
                        SettingsRule
                    )
from jpegexport.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )

# -----------------------------------------------------------------------------


class JESettingsValues(object):
    RENDER_MODE_FINAL =                                     'final'
    RENDER_MODE_DIFFVALUE =                                 'diff-value'
    RENDER_MODE_DIFFBITS =                                  'diff-bits'
    RENDER_MODE_SOURCE =                                    'source'

    # 0=4:2:0 (smallest file size)   1=4:2:2    2=4:4:0     3=4:4:4 (Best quality)
    JPEG_SUBSAMPLING_420 =                                  0
    JPEG_SUBSAMPLING_422 =                                  1
    JPEG_SUBSAMPLING_440 =                                  2
    JPEG_SUBSAMPLING_444 =                                  3

class JESettingsKey(SettingsKey):
    CONFIG_FILE_LASTPATH =                                  'config.file.lastPath'

    CONFIG_JPEG_QUALITY =                                   'config.jpeg.quality'
    CONFIG_JPEG_SMOOTHING =                                 'config.jpeg.smoothing'
    CONFIG_JPEG_SUBSAMPLING =                               'config.jpeg.subsampling'
    CONFIG_JPEG_PROGRESSIVE =                               'config.jpeg.progressive'
    CONFIG_JPEG_OPTIMIZE =                                  'config.jpeg.optimize'
    CONFIG_JPEG_SAVEPROFILE =                               'config.jpeg.saveProfile'
    CONFIG_JPEG_TRANSPFILLCOLOR =                           'config.jpeg.transparencyFillcolor'

    CONFIG_RENDER_MODE =                                    'config.render.mode'

class JESettings(Settings):
    """Manage JPEG Export settings (keep in memory last preferences used for export)

    Configuration is saved as JSON file
    """

    def __init__(self, pluginId=None):
        """Initialise settings"""
        if pluginId is None or pluginId == '':
            pluginId = 'jpegexport'

        rules = [
            SettingsRule(JESettingsKey.CONFIG_FILE_LASTPATH,                                '',                         SettingsFmt(str)),

            SettingsRule(JESettingsKey.CONFIG_JPEG_QUALITY,                                 85,                         SettingsFmt(int, (0, 100) )),
            SettingsRule(JESettingsKey.CONFIG_JPEG_SMOOTHING,                               15,                         SettingsFmt(int, (0, 100) )),
            SettingsRule(JESettingsKey.CONFIG_JPEG_SUBSAMPLING,                             JESettingsValues.JPEG_SUBSAMPLING_444,
                                                                                                                        SettingsFmt(int, [JESettingsValues.JPEG_SUBSAMPLING_420,
                                                                                                                                          JESettingsValues.JPEG_SUBSAMPLING_422,
                                                                                                                                          JESettingsValues.JPEG_SUBSAMPLING_440,
                                                                                                                                          JESettingsValues.JPEG_SUBSAMPLING_444])),
            SettingsRule(JESettingsKey.CONFIG_JPEG_PROGRESSIVE,                             True,                       SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_JPEG_OPTIMIZE,                                True,                       SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_JPEG_SAVEPROFILE,                             False,                      SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR,                         '#ffffff',                  SettingsFmt(str)),

            SettingsRule(JESettingsKey.CONFIG_RENDER_MODE,                                  JESettingsValues.RENDER_MODE_FINAL,
                                                                                                                        SettingsFmt(str, [JESettingsValues.RENDER_MODE_FINAL,
                                                                                                                                          JESettingsValues.RENDER_MODE_DIFFVALUE,
                                                                                                                                          JESettingsValues.RENDER_MODE_DIFFBITS,
                                                                                                                                          JESettingsValues.RENDER_MODE_SOURCE])),
        ]

        super(JESettings, self).__init__(pluginId, rules)
