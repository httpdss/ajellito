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
