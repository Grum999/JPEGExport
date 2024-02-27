# -----------------------------------------------------------------------------
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


from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal,
        QSettings,
        QStandardPaths
    )

import os

from jpegexport.pktk.widgets.wcolorselector import WColorPicker
from jpegexport.pktk.modules.settings import (
                        Settings,
                        SettingsFmt,
                        SettingsKey,
                        SettingsRule
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

    UNIT_PX =                                               'px'
    UNIT_PCT =                                              '%'
    UNIT_PX_WIDTH =                                         'wpx'
    UNIT_PX_HEIGHT =                                        'hpx'

    FILTER_BSPLINE =                                        'BSpline'
    FILTER_BELL =                                           'Bell'
    FILTER_BICUBIC =                                        'Bicubic'
    FILTER_BILINEAR =                                       'Bilinear'
    FILTER_HERMITE =                                        'Hermite'
    FILTER_LANCZOS3 =                                       'Lanczos3'
    FILTER_MITCHELL =                                       'Mitchell'
    FILTER_NEAREST_NEIGHBOUR =                              'Box'

    VIEWMODE_LIST = 0
    VIEWMODE_ICON = 1


class JESettingsKey(SettingsKey):
    CONFIG_FILE_LASTPATH =                                  'config.file.lastPath'

    CONFIG_WINDOW_GEOMETRY_SIZE_WIDTH =                     'config.window.geometry.size.width'
    CONFIG_WINDOW_GEOMETRY_SIZE_HEIGHT =                    'config.window.geometry.size.height'
    CONFIG_WINDOW_GEOMETRY_POSITION_X =                     'config.window.geometry.position.x'
    CONFIG_WINDOW_GEOMETRY_POSITION_Y =                     'config.window.geometry.position.y'

    CONFIG_SETUPMANAGER_ZOOMLEVEL =                         'config.setupManager.zoomLevel'
    CONFIG_SETUPMANAGER_COLUMNWIDTH =                       'config.setupManager.columnWidth'
    CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_VIEWMODE =   'config.setupManager.properties.dlgBox.icon.viewMode'
    CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_ZOOMLEVEL =  'config.setupManager.properties.dlgBox.icon.zoomLevel'
    CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_COLORPICKER =     'config.setupManager.properties.dlgBox.colorPicker'
    CONFIG_SETUPMANAGER_LASTFILE =                          'config.setupManager.lastFile'
    CONFIG_SETUPMANAGER_COLORPICKER_COMPACT =               'config.setupManager.colorPicker.compact'
    CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_VISIBLE =       'config.setupManager.colorPicker.palette.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_DEFAULT =       'config.setupManager.colorPicker.palette.default'
    CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_VISIBLE =        'config.setupManager.colorPicker.colorWheel.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_CPREVIEW =       'config.setupManager.colorPicker.colorWheel.colorPreview'
    CONFIG_SETUPMANAGER_COLORPICKER_CCOMBINATION =          'config.setupManager.colorPicker.colorCombination'
    CONFIG_SETUPMANAGER_COLORPICKER_CCSS =                  'config.setupManager.colorPicker.colorCss.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_VISIBLE =   'config.setupManager.colorPicker.colorSlider.rgb.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_ASPCT =     'config.setupManager.colorPicker.colorSlider.rgb.asPct'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_VISIBLE =  'config.setupManager.colorPicker.colorSlider.cmyk.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_ASPCT =    'config.setupManager.colorPicker.colorSlider.cmyk.asPct'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_VISIBLE =   'config.setupManager.colorPicker.colorSlider.hsl.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_ASPCT =     'config.setupManager.colorPicker.colorSlider.hsl.asPct'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_VISIBLE =   'config.setupManager.colorPicker.colorSlider.hsv.visible'
    CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_ASPCT =     'config.setupManager.colorPicker.colorSlider.hsv.asPct'

    CONFIG_RENDER_MODE =                                    'config.render.mode'

    CONFIG_JPEG_QUALITY =                                   'config.options.jpeg.quality'
    CONFIG_JPEG_SMOOTHING =                                 'config.options.jpeg.smoothing'
    CONFIG_JPEG_SUBSAMPLING =                               'config.options.jpeg.subsampling'
    CONFIG_JPEG_PROGRESSIVE =                               'config.options.jpeg.progressive'
    CONFIG_JPEG_OPTIMIZE =                                  'config.options.jpeg.optimize'
    CONFIG_JPEG_SAVEPROFILE =                               'config.options.jpeg.saveProfile'
    CONFIG_JPEG_TRANSPFILLCOLOR =                           'config.options.jpeg.transparencyFillcolor'

    CONFIG_MISC_CROP_ACTIVE =                               'config.options.crop.active'
    CONFIG_MISC_RESIZE_ACTIVE =                             'config.options.resize.active'
    CONFIG_MISC_RESIZE_UNIT =                               'config.options.resize.unit'
    CONFIG_MISC_RESIZE_PCT_VALUE =                          'config.options.resize.pct.value'
    CONFIG_MISC_RESIZE_PX_WIDTH =                           'config.options.resize.px.width'
    CONFIG_MISC_RESIZE_PX_HEIGHT =                          'config.options.resize.px.height'
    CONFIG_MISC_RESIZE_FILTER =                             'config.options.resize.filter'

    CONFIG_PATH_TGTMODE =                                   'config.options.path.tgtMode'
    CONFIG_PATH_USRPATH =                                   'config.options.path.userPath'

    CONFIG_OPT_INDEX =                                      'config.options.pageIndex'

class JESettings(Settings):
    """Manage JPEG Export settings (keep in memory last preferences used for export)

    Configuration is saved as JSON file
    """

    def __init__(self, pluginId=None):
        """Initialise settings"""
        if pluginId is None or pluginId == '':
            pluginId = 'jpegexport'


        rules = [
            SettingsRule(JESettingsKey.CONFIG_FILE_LASTPATH,                                os.path.normpath(QStandardPaths.writableLocation(QStandardPaths.HomeLocation)),
                                                                                                                                SettingsFmt(str)),

            SettingsRule(JESettingsKey.CONFIG_WINDOW_GEOMETRY_SIZE_WIDTH,                   0,  SettingsFmt(int)),
            SettingsRule(JESettingsKey.CONFIG_WINDOW_GEOMETRY_SIZE_HEIGHT,                  0,  SettingsFmt(int)),
            SettingsRule(JESettingsKey.CONFIG_WINDOW_GEOMETRY_POSITION_X,                   0,  SettingsFmt(int)),
            SettingsRule(JESettingsKey.CONFIG_WINDOW_GEOMETRY_POSITION_Y,                   0,  SettingsFmt(int)),

            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_LASTFILE,                        '', SettingsFmt(str)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_ZOOMLEVEL,                       3,  SettingsFmt(int, [0, 1, 2, 3, 4])),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLUMNWIDTH,                     -1, SettingsFmt(int)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_ZOOMLEVEL, 3, SettingsFmt(int, [0, 1, 2, 3, 4, 5, 6])),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_PROPERTIES_DLGBOX_ICON_VIEWMODE,  JESettingsValues.VIEWMODE_LIST,
                                                                                             SettingsFmt(int,
                                                                                                         [JESettingsValues.VIEWMODE_LIST,
                                                                                                          JESettingsValues.VIEWMODE_ICON
                                                                                                          ]
                                                                                                         ),
                         ),

            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_COMPACT,              True,      SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_VISIBLE,      True,      SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_DEFAULT,      "Default", SettingsFmt(str)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_VISIBLE,       False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_CPREVIEW,      True,      SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CCOMBINATION,         0,         SettingsFmt(int, [0, 1, 2, 3, 4, 5])),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CCSS,                 False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_VISIBLE,  False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_ASPCT,    False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_VISIBLE, False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_ASPCT,   False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_VISIBLE,  False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_ASPCT,    False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_VISIBLE,  False,     SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_ASPCT,    False,     SettingsFmt(bool)),

            SettingsRule(JESettingsKey.CONFIG_OPT_INDEX,                                    0,                                  SettingsFmt(int, [0, 1, 2])),

            SettingsRule(JESettingsKey.CONFIG_JPEG_QUALITY,                                 85,                                 SettingsFmt(int, (0, 100))),
            SettingsRule(JESettingsKey.CONFIG_JPEG_SMOOTHING,                               15,                                 SettingsFmt(int, (0, 100))),
            SettingsRule(JESettingsKey.CONFIG_JPEG_SUBSAMPLING,                             JESettingsValues.JPEG_SUBSAMPLING_444,
                                                                                                                                SettingsFmt(int, [JESettingsValues.JPEG_SUBSAMPLING_420,
                                                                                                                                                  JESettingsValues.JPEG_SUBSAMPLING_422,
                                                                                                                                                  JESettingsValues.JPEG_SUBSAMPLING_440,
                                                                                                                                                  JESettingsValues.JPEG_SUBSAMPLING_444])),
            SettingsRule(JESettingsKey.CONFIG_JPEG_PROGRESSIVE,                             True,                               SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_JPEG_OPTIMIZE,                                True,                               SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_JPEG_SAVEPROFILE,                             False,                              SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_JPEG_TRANSPFILLCOLOR,                         '#ffffff',                          SettingsFmt(str)),

            SettingsRule(JESettingsKey.CONFIG_PATH_TGTMODE,                                 'src',                              SettingsFmt(str, ['src', 'usr'])),
            SettingsRule(JESettingsKey.CONFIG_PATH_USRPATH,                                 '',                                 SettingsFmt(str)),

            SettingsRule(JESettingsKey.CONFIG_RENDER_MODE,                                  JESettingsValues.RENDER_MODE_FINAL, SettingsFmt(str, [JESettingsValues.RENDER_MODE_FINAL,
                                                                                                                                                  JESettingsValues.RENDER_MODE_DIFFVALUE,
                                                                                                                                                  JESettingsValues.RENDER_MODE_DIFFBITS,
                                                                                                                                                  JESettingsValues.RENDER_MODE_SOURCE])),

            SettingsRule(JESettingsKey.CONFIG_MISC_CROP_ACTIVE,                             False,                              SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_MISC_RESIZE_ACTIVE,                           False,                              SettingsFmt(bool)),
            SettingsRule(JESettingsKey.CONFIG_MISC_RESIZE_UNIT,                             JESettingsValues.UNIT_PX,           SettingsFmt(str, [JESettingsValues.UNIT_PX,
                                                                                                                                                  JESettingsValues.UNIT_PCT,
                                                                                                                                                  JESettingsValues.UNIT_PX_WIDTH,
                                                                                                                                                  JESettingsValues.UNIT_PX_HEIGHT])),
            SettingsRule(JESettingsKey.CONFIG_MISC_RESIZE_PCT_VALUE,                        100.00,                             SettingsFmt(float, (0.01, 1000.00))),
            SettingsRule(JESettingsKey.CONFIG_MISC_RESIZE_PX_WIDTH,                         1000,                               SettingsFmt(int, (1, 32000))),
            SettingsRule(JESettingsKey.CONFIG_MISC_RESIZE_PX_HEIGHT,                        1000,                               SettingsFmt(int, (1, 32000))),
            SettingsRule(JESettingsKey.CONFIG_MISC_RESIZE_FILTER,                           JESettingsValues.FILTER_BICUBIC,    SettingsFmt(str, [JESettingsValues.FILTER_BSPLINE,
                                                                                                                                                  JESettingsValues.FILTER_BELL,
                                                                                                                                                  JESettingsValues.FILTER_BICUBIC,
                                                                                                                                                  JESettingsValues.FILTER_BILINEAR,
                                                                                                                                                  JESettingsValues.FILTER_HERMITE,
                                                                                                                                                  JESettingsValues.FILTER_LANCZOS3,
                                                                                                                                                  JESettingsValues.FILTER_MITCHELL,
                                                                                                                                                  JESettingsValues.FILTER_NEAREST_NEIGHBOUR])),
        ]
        super(JESettings, self).__init__(pluginId, rules)

    @staticmethod
    def getTxtColorPickerLayout():
        """Convert picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setConstraintSize(True)
        tmpColorPicker.setOptionCompactUi(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_COMPACT))
        tmpColorPicker.setOptionShowColorPalette(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_VISIBLE))
        tmpColorPicker.setOptionColorPalette(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_DEFAULT))
        tmpColorPicker.setOptionShowColorWheel(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_VISIBLE))
        tmpColorPicker.setOptionShowPreviewColor(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_CPREVIEW))
        tmpColorPicker.setOptionShowColorCombination(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CCOMBINATION))
        tmpColorPicker.setOptionShowCssRgb(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CCSS))
        tmpColorPicker.setOptionShowColorRGB(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorRGB(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_ASPCT))
        tmpColorPicker.setOptionShowColorCMYK(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorCMYK(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_ASPCT))
        tmpColorPicker.setOptionShowColorHSV(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSV(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_ASPCT))
        tmpColorPicker.setOptionShowColorHSL(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSL(JESettings.get(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_ASPCT))
        tmpColorPicker.setOptionShowColorAlpha(False)
        return tmpColorPicker.optionLayout()

    @staticmethod
    def setTxtColorPickerLayout(layout):
        """Convert color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionLayout(layout)

        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_COMPACT, tmpColorPicker.optionCompactUi())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_VISIBLE, tmpColorPicker.optionShowColorPalette())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_PALETTE_DEFAULT, tmpColorPicker.optionColorPalette())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_VISIBLE, tmpColorPicker.optionShowColorWheel())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CWHEEL_CPREVIEW, tmpColorPicker.optionShowPreviewColor())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CCOMBINATION, tmpColorPicker.optionShowColorCombination())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CCSS, tmpColorPicker.optionShowColorCssRGB())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_VISIBLE, tmpColorPicker.optionShowColorRGB())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_RGB_ASPCT, tmpColorPicker.optionDisplayAsPctColorRGB())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_VISIBLE, tmpColorPicker.optionShowColorCMYK())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_CMYK_ASPCT, tmpColorPicker.optionDisplayAsPctColorCMYK())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_VISIBLE, tmpColorPicker.optionShowColorHSL())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSL_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSL())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_VISIBLE, tmpColorPicker.optionShowColorHSV())
        JESettings.set(JESettingsKey.CONFIG_SETUPMANAGER_COLORPICKER_CSLIDER_HSV_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSV())
