# JPEG Export

A plugin for [Krita](https://krita.org).


## What is JPEG Export?
*JPEG Export* is a Python plugin made for [Krita](https://krita.org) (free professional and open-source painting program).


Krita already allows to export documents as JPEG, but for whom need to find the the right balance between file size and image quality, Krita export functionality doesn't really help.

Basically, the plugin use Krita JPEG export capabilities, but add an improved interface to let user being able to determinate best export options to apply to image.


## Screenshots

*Main interface, final result preview*

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/main-final.jpeg)

*Main interface, difference (bits) result preview*

![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/main-diff.jpeg)


## Functionalities

Here the list of functionalities:
- Provides most of JPEG export options
- Real time (~1s) export result preview
- Exported result preview is rendered in a Krita view
  - *Allows to zoom and scroll on export result preview to check for JPEG compression artifacts*
- Exported JPEG file size provided
- Different render modes (Final result, difference with source)


## Download, Install & Execute

### Download
+ **[ZIP ARCHIVE - v1.1.0](https://github.com/Grum999/JPEGExport/releases/download/1.1.0/jpegexport.zip)**
+ **[SOURCE](https://github.com/Grum999/JPEGExport)**


### Installation

Plugin installation in [Krita](https://krita.org) is not intuitive and needs some manipulation:

1. Open [Krita](https://krita.org) and go to **Tools** -> **Scripts** -> **Import Python Plugins...** and select the **jpegexport.zip** archive and let the software handle it.
2. Restart [Krita](https://krita.org)
3. To enable *JPEG Export* go to **Settings** -> **Configure Krita...** -> **Python Plugin Manager** and click the checkbox to the left of the field that says **JPEG Export**.
4. Restart [Krita](https://krita.org)


### Execute

User of Krita 4: go to **Tools**>**Scripts** menu and select **JPEG Export...**

User of Krita 5: go to **File** menu and select **JPEG Export...**


### Tested platforms

Plugin has been tested with Krita 4.4.7 and Krita 5.0.0-beta2 (appimage) on Linux Debian 10

Currently don't kwow if plugin works on Windows and MacOs, but as plugin don't use specific OS functionalities and/resources, it should be ok.



## Plugin's life

### What's new?

_[2021-11-07] Version 1.1.0_ *[Show detailed release content](https://github.com/Grum999/JPEGExport/blob/main/releases-notes/RELEASE-1.1.0.md)*
- Implement *Crop to selection*
- Implement *Resize exported document*
- Implement *Exported document dimensions*
- Improve *Render preview*

_[2021-05-18] Version 1.0.0_ *[Show detailed release content](https://github.com/Grum999/JPEGExport/blob/main/releases-notes/RELEASE-1.0.0.md)*
- First implemented/released version!



### Bugs

Probably.



### What’s next?

Currently, nothing :-)
Any idea are welcome.


## License

### *JPEG Export* is released under the GNU General Public License (version 3 or any later version).

*JPEG Export* is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

*JPEG Export* is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should receive a copy of the GNU General Public License along with *Buli Commander*. If not, see <https://www.gnu.org/licenses/>.


Long story short: you're free to download, modify as well as redistribute *JPEG Export* as long as this ability is preserved and you give contributors proper credit. This is the same license under which Krita is released, ensuring compatibility between the two.
