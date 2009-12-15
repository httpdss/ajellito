import odf.opendocument as opendocument
import odf.style
from odf.table import Table, TableColumn, TableRow, TableCell
from odf.namespaces import OFFICENS, TABLENS, TEXTNS
from odf.text import P, S, LineBreak, Span, Section, List, ListItem
from odf.draw import Frame, TextBox
import odf.element as element

import html5lib
import copy

def Style(uid, family, props):
    style = odf.style.Style(name='%s-%s' % (family, str(uid)), family=family)

    for k, v in props:
        if k == 'bold' and v:
            style.addElement(odf.style.TextProperties(fontweight="bold"))
        elif k == 'italic' and v:
            style.addElement(odf.style.TextProperties(fontstyle="italic"))
        elif k == 'underline' and v:
            style.addElement(odf.style.TextProperties(textunderlinestyle='solid', textunderlinewidth='auto', textunderlinecolor='font-color'))
        elif k == 'background' and family == 'table-cell':
            style.addElement(odf.style.TableCellProperties(backgroundcolor=v))
        elif k == 'color':
            style.addElement(odf.style.TextProperties(color=v))
        elif k == 'strike':
            style.addElement(odf.style.TextProperties(textlinethroughstyle='solid'))
        elif k == 'align' and family == 'paragraph':
            style.addElement(odf.style.ParagraphProperties(textalign=v, justifysingleword='false'))
        else:
            raise Exception('Unsupported stye attribute %s' % k)

    return style

class Formula(object):
    def __init__(self, f, v):
        self.formula = f
        self.value = v

class HTML(unicode):
    def __new__(cls, s):
        return unicode.__new__(cls, s)

    def __init__(self, s):
        self.html = True

class Sheet:
    def __init__(self, name, calc):
        self._cells = {}
        self._rows = 0
        self._cols = 0
        self._calc = calc
        self._name = name

    def style(self, family, props):
        return self._calc.style(family, props)

    def render(self):
        table = Table(name=self._name)
        table.addElement(TableColumn(stylename=self._calc.style_co1))

        for row in range(self._rows):
            tr = TableRow()
            table.addElement(tr)

            for col in range(self._cols):
                try:
                    tc = self._cells[(row, col)]
                except KeyError:
                    tc = TableCell()
                tr.addElement(tc)
        return table

    def write(self, cell, value, style={}):
        row, col = cell
        if row >= self._rows: self._rows = row + 1
        if col >= self._cols: self._cols = col + 1

        tc = TableCell(stylename=self.style('table-cell', style))

        if isinstance(value, Formula):
            tc.setAttrNS(TABLENS, 'formula', value.formula)
            tc.setAttrNS(OFFICENS, 'value', str(value.value))
            tc.setAttrNS(OFFICENS, 'value-type', 'float')
            tc.addElement(P(text=unicode('0', 'utf-8')))

        elif isinstance(value, HTML):
            tc.setAttrNS(OFFICENS, 'value-type', 'string')
            self._calc.HTML(html5lib.HTMLParser().parse(value), tc)

        elif isinstance(value, basestring):
            tc.setAttrNS(OFFICENS, 'value-type', 'string')
            tc.addElement(P(text=value))

        elif isinstance(value, (float, int)):
            tc.setAttrNS(OFFICENS, 'value-type', 'float')
            tc.setAttrNS(OFFICENS, 'value', str(value))
            tc.addElement(P(text=str(value)))

        elif isinstance(value, element.Element):
            tc.setAttrNS(OFFICENS, 'value-type', 'string')
            tc.addElement(value)

        self._cells[cell] = tc

class OpenDocument(object):
    def __init__(self, doc):
        self._doc = doc

        self._styles = {'':{}}

        self.debug = False

    def style(self, family, props):
        if not self._styles.has_key(family):
            self._styles[family] = {}

        attrs = []
        for k, v in props.items():
            if v == False:
                continue
            attrs.append((k.lower(), v))
        attrs.sort(lambda a, b: cmp(a[0], b[0]))
        attrs = tuple(attrs)
        try:
            return self._styles[family][attrs]
        except KeyError:
            s = Style(len(self._styles[family].keys()), family, attrs)
            self._styles[family][attrs] = s
            self._doc.automaticstyles.addElement(s)
            return s

class Calc(OpenDocument):
    def __init__(self, sheetname):
        super(Calc, self).__init__(opendocument.OpenDocumentSpreadsheet())

        self._sheetnames = []
        self._sheets = {}
        self._sheet = None
        self._olcount = 0

        self.style_co1 = self.style('table-column', {})

        self.select(sheetname)

    @staticmethod
    def cellname(row, col):
        name = ''
        col += 1
        while col > 26:
            name = '%s%s' % (chr(64 + (col % 26)), name)
            col = col / 26
        name = '%s%s%d' % (chr(64 + col), name, row + 1)
        return name

    def P(self, root, p):
        if p is None:
            p = P()
            root.addElement(p)
        return p

    def HTML(self, chunk, root, p=None, style={}, listtype=None):
        for child in chunk.childNodes:
            if child.name is None:
                tag = None
            else:
                tag = child.name.lower()
    
            if tag is None:
                p = self.P(root, p)

                if child.value[0].isspace():
                    p.addElement(S())
                s = Span(text=child.value.strip(), stylename=self.style('text', style))
                p.addElement(s)
                if child.value[-1].isspace():
                    p.addElement(S())

            elif tag in ['br', 'hr']:
                root.addElement(P())
                p = None

            elif tag in ['p', 'div']: # handle alignment
                if child.attributes.has_key('align'):
                    align = {'right': 'end', 'left': False, 'center': 'center', 'justify': 'justify'}[child.attributes['align']]
                    p = P(stylename=self.style('paragraph', {'align': align}))
                else:
                    p = P()
                root.addElement(p)
                self.HTML(child, root, p, style, listtype)

            elif tag in ['i', 'em']:
                _style = copy.copy(style)
                _style.update({'italic': True})
                self.HTML(child, root, p, _style, listtype)

            elif tag in ['b', 'strong']:
                _style = copy.copy(style)
                _style.update({'bold': True})
                self.HTML(child, root, p, _style, listtype)

            elif tag == 'u':
                _style = copy.copy(style)
                _style.update({'underline': True})
                self.HTML(child, root, p, _style, listtype)

            elif tag == 'strike':
                _style = copy.copy(style)
                _style.update({'strike': True})
                self.HTML(child, root, p, _style, listtype)

            elif tag in ['ol', 'ul']:
                self._olcount = 0
                self.HTML(child, root, p, style, tag)

            elif tag in ['html', 'head', 'body', 'table', 'tbody', 'tr', 'td']:
                self.HTML(child, root, p, style, listtype)

            elif tag == 'li':
                p = self.P(root, None)

                if listtype == 'ul':
                    s = Span(text='*', stylename=self.style('text', style))
                elif listtype == 'ol':
                    self._olcount += 1
                    s = Span(text='%d.' % self._olcount, stylename=self.style('text', style))
                else:
                    raise Exception('List type not set')

                p.addElement(s)
                p.addElement(S())
                self.HTML(child, root, p, style, listtype)

            ## later we'll just ignore what we don't understand, but
            ## right now I want explicit notification.
            else:
                if self.debug: print 'Unexpected tag', tag
                self.HTML(child, root, p, style, listtype)
    
        return root

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._sheets[self._sheetnames[key]]
        try:
            sheet = self._sheets[key]
        except KeyError:
            self._sheetnames.append(key)
            sheet = Sheet(key, self)
            self._sheets[key] = sheet
        return sheet

    def select(self, key):
        self._sheet = self[key]

    def write(self, cell, value, style={}):
        self._sheet.write(cell, value, style)

    def save(self, f):
        for sheet in [self._sheets[name] for name in self._sheetnames]:
            self._doc.spreadsheet.addElement(sheet.render())
        self._doc.write(f)

import reportlab.platypus as platypus
import reportlab.lib

#http://www.hoboes.com/Mimsy/hacks/multiple-column-pdf/
class Cards(object):
    def __init__(self, spec):
        inch = reportlab.lib.units.inch
        style = reportlab.lib.styles.getSampleStyleSheet() 
        para = platypus.Paragraph(para, style['Normal'])

        pagesize = getattr(reportlab.lib.pagesizes, spec.page.upper)
        document = platypus.BaseDocTemplate('/var/www/auto/sign/test.pdf', pagesize=pagesize)
        frameCount = 2
        frameWidth = document.width/frameCount
        frameHeight = document.height-.05*inch
        frames = []
        #construct a frame for each column

        for frame in range(frameCount):
            leftMargin = document.leftMargin + frame*frameWidth
            column = platypus.Frame(leftMargin, document.bottomMargin, frameWidth, frameHeight)
            frames.append(column)

        template = platypus.PageTemplate(frames=frames)
        document.addPageTemplates(template)
        document.build(posts) 
