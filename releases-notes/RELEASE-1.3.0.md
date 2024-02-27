# JPEG Export :: Release 1.3.0 [2024-02-27]

# Main Interface

## Implement *Improve UI*

Window size has been reduced to let it open on smaller screens. 
Then, to be able to put all options (and taking in account new one), the user interface has been reviewed. 

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow.jpeg)

| Reference | Description                                                |
|-----------|------------------------------------------------------------|
| 1         | Access to export settings & settings manager through tabs |
| 2         | Access to miscellaneous export settings<br><br>*Crop & Resize options*<br>![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow_exportedContent.jpeg)<br>*Crop & Resize options*<br>![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow_jpegOptions.jpeg) |


[Feature #5](https://github.com/Grum999/JPEGExport/issues/5)

## Implement *Allow to define target path*

Options to define target document path allows to quickly define default path where document will be saved

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow_targetDocument.jpeg)

| Target path                   | Description                                                                                   |
|-------------------------------|-----------------------------------------------------------------------------------------------|
| **Same source than document** | Default path defined for exported JPEG document will be the same than original source file    |
| **Last used directory**       | Default path defined for exported JPEG document will be the same than one used on last export |
| **User defined**              | Default path defined for exported JPEG document will be the one defined by user               |

> Note:
> Changing option value when path is already defined will automatically apply new path from selected option 

[Feature #6](https://github.com/Grum999/JPEGExport/issues/6)


## Implement *Settings manager*

The *Settings manager* let the possibility to manage different export options according to final use of JPEG file.

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow_settingsManager.jpeg)

| Reference | Description                                                                                                                                                                                                           |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1         | Manage settings import/export<br>- New setting pool<br>- Import a setting pool<br>- Export settings pool<br><br>This can be useful to manage backup files or easily use the same settings across different computers  |
| 2         | Manage settings<br>- Create a new settings from current export setup<br>- Create a new folder<br>- Edit selected item<br>- Delete selected item                                                                       |                                                                     
| 3         | Apply selected settings<br>*Settings will be applied for export setup*                                                                                                                                                |  
| 4         | Pool settings<br>Drag'n'Drop to reorganise items                                                                                                                                                                      |
| 5         | Current settings pool file                                                                                                                                                                                            |    

Editing a settings in pool allow to define:
- Title
- Icon
- Description

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow_settingsManager_edit1.jpeg)

Export setup properties for settings are visible in *Setup preview*  

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-3-0_mainwindow_settingsManager_edit2.jpeg)

[Feature #4](https://github.com/Grum999/JPEGExport/issues/4)

## Implement *Keep window position*

Last *JPEG Export* main window position & size are kept and re-used on next plugin use.

[Feature #1](https://github.com/Grum999/JPEGExport/issues/1)

# Fix bugs

## User interface - *Save window is behind*

On Windows, the *save* dialog box was stucked behind main plugin window.
This is now fixed.

[Bug #2](https://github.com/Grum999/JPEGExport/issues/2)
