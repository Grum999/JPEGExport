# JPEG Export

A plugin for [Krita](https://krita.org).


## What is JPEG Export?
*JPEG Export* is a Python plugin made for [Krita](https://krita.org) (free professional and open-source painting program).


Krita already allows to export documents as JPEG, but for whom need to find the the right balance between file size and image quality, Krita export functionality doesn't really help.

Basically, the plugin use Krita JPEG export capabilities, but add an improved interface to let user being able to determinate best export options to apply to image.


## Screenshots

Main interface, final result preview
![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/main-final.jpeg)

Main interface, difference (bits) result preview
![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/main-final.jpeg)


## Functionalities

Here a list of some functionalities:
- Provides most of JPEG export options
- Exported result preview in a Krita view (allows to zoom and scroll exported result to check for JPEG compression artifacts)
- Exported result file size
- Different render mode (Final result, difference with source)


## Download, Install & Execute

### Download
+ **[ZIP ARCHIVE - v1.0.0a](https://github.com/Grum999/JPEGExport/releases/download/1.0.0a/jpegexport.zip)**
+ **[SOURCE](https://github.com/Grum999/JPEGExport)**


### Installation

Plugin installation in [Krita](https://krita.org) is not intuitive and needs some manipulation:

1. Open [Krita](https://krita.org) and go to **Tools** -> **Scripts** -> **Import Python Plugins...** and select the **jpegexport.zip** archive and let the software handle it.
2. Restart [Krita](https://krita.org)
3. To enable *JPEG Export* go to **Settings** -> **Configure Krita...** -> **Python Plugin Manager** and click the checkbox to the left of the field that says **JPEG Export**.
4. Restart [Krita](https://krita.org)


### Execute

When you want to execute *JPEG Export*, simply go to **File** menu and select **JPEG Export...**.


### Tested platforms

> Notes:
> - Plugin is not compatible with Krita 4.x.x; you must have at least Krita 5.x.x
> - As currently Krita 5 is still in pre-alpha version, plugin is in alpha version and as long as Krita 5 won't be available as a stable version, plugin will be provided as alpha version

Plugin has been tested with Krita 5.0.0 (appimage) on Linux Debian 10

Currently don't kwow if plugin works on Windows and MacOs, but as plugin don't use specific OS functionalities and/resources, it should be ok.



## Plugin's life

### What's new?

_[2021-05-xx] Version 1.0.0a_ *[Show detailed release content](https://github.com/Grum999/JPEGExport/blob/main/releases-notes/RELEASE-1.0.0a.md)*

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
