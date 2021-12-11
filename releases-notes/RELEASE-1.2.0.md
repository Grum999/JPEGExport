# JPEG Export :: Release 1.2.0 [2021-12-11]

# Improvements

## Implement *Resize from width or from height*

Option to allow to resize exported document during export has been improved.

To existing units *pixels* `px` and *percentage* `%`, resize option provides 2 new possible units:
- *Pixels width* `px (width)`: allows define a fixed width, height is defined automatically according to image ratio
- *Pixels height* `px (height)`: allows define a fixed height, width is defined automatically according to image ratio


# Fixed bugs

## Errors from *Cleanup and missing controls*

When validating/cancelling export or closing document (source or preview) there was some invalid cleanup and potential error messages.

Fixed: tried to made more cleanup and controls.

## User Interface *Missing icons*

Icons were missing.

Fixed for <u>Krita 5.0.0 only</u>


## User Interface *Menu not in the right place*

In some specific case, the action **JPEG Export...** is not properly located in **File** menu.

Really hard to reproduce the case, but tried to fix it...
