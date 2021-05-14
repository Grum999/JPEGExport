from .jpegexport import JpegExport

# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = JpegExport(parent=app)
app.addExtension(extension)
