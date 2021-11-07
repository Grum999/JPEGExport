# JPEG Export :: Release 1.1.0 [2021-11-07]


*Interface for v1.1.0*
![Main interface](https://github.com/Grum999/JPEGExport/raw/main/screenshots/r1-1-0_mainwindow.jpeg)


## Implement *Crop to selection*

If a selection exists on source document, option to crop export to selection is available.


## Implement *Resize exported document*

An option to allow to resize exported document during export.

- BSpline
Resize method can use Krita's filters:
- Bell
- Bicubic
- Bilinear
- Hermite
- Lanczos3
- Mitchell
- Nearest neighbour

New size can be defined:
- In percentage of original document (or if crop mode is checked, in percentage of selection)
- In pixels
  - *Note: pixels size define maximum bounds within the image will be resized, keeping source width/height ratio; it doesn't define the final document size*

## Implement *Exported document dimensions*

As *Crop* and *Resize* options let the possibility to get a document for which dimensions are not the same than original document, the final document dimensions are provided


## Improve *Render preview*
Render preview mode **Difference (value)** has been improved.
Use *Divisive Modulo - Continuous* blending mode instead of *Difference* provides a better render of difference values (more visible).
