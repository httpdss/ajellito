try:
    import pyExcelerator
    import pyExcelerator.CompoundDoc
    import types

    ## this is a monkey patch to trick pyExcelerator into saving to a
    ## stream instead of to a file(name)
    def pyexcelerator_compounddoc_xlsdoc_save(self, filename, stream):
        # 1. Align stream on 0x1000 boundary (and therefore on sector boundary)
        padding = '\x00' * (0x1000 - (len(stream) % 0x1000))
        self.book_stream_len = len(stream) + len(padding)

        self._XlsDoc__build_directory()
        self._XlsDoc__build_sat()
        self._XlsDoc__build_header()

        if isinstance(filename, types.StringTypes):
            f = file(filename, 'wb')
        else:
            f = filename
        f.write(self.header)
        f.write(self.packed_MSAT_1st)
        f.write(stream)
        f.write(padding)
        f.write(self.packed_MSAT_2nd)
        f.write(self.packed_SAT)
        f.write(self.dir_stream)
        f.close()

    pyExcelerator.CompoundDoc.XlsDoc.save = pyexcelerator_compounddoc_xlsdoc_save
    EXCEL_ENABLED = True

except ImportError:
    EXCEL_ENABLED = False

import settings

try:
    settings.CACHE_BACKEND
    CACHE_ENABLED = True
except AttributeError:
    CACHE_ENABLED = False

try:
    UNRESTRICTED_SIZE = settings.UNRESTRICTED_SIZE
except AttributeError:
    UNRESTRICTED_SIZE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot
    MATPLOTLIB_ENABLED = True
except ImportError:
    MATPLOTLIB_ENABLED = False

ITERATION_STATUS_FLASH_CHART = getattr(settings, 'ITERATION_STATUS_FLASH_CHART', True)

PRINTABLE_CARDS = settings.CARD_INFO
