# -*- coding: utf-8 -*-

import odf.opendocument as opendocument
import odf.style
import odf.table
from odf.namespaces import OFFICENS, TABLENS, TEXTNS
import odf.text
import odf.element as element
from types import TupleType, ListType

import html5lib
import copy
import os.path
import math

try:
    import cPickle as pickle
except ImportError:
    import pickle

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
        elif k == 'columnwidth' and family == 'table-column':
            style.addElement(odf.style.TableColumnProperties(columnwidth=v))
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
        table = odf.table.Table(name=self._name)
        table.addElement(odf.table.TableColumn(stylename=self._calc.style_co1))

        for row in range(self._rows):
            tr = odf.table.TableRow()
            table.addElement(tr)

            for col in range(self._cols):
                try:
                    tc = self._cells[(row, col)]
                except KeyError:
                    tc = odf.table.TableCell()
                tr.addElement(tc)
        return table

    def write(self, cell, value, style={}):
        row, col = cell
        if row >= self._rows: self._rows = row + 1
        if col >= self._cols: self._cols = col + 1

        tc = odf.table.TableCell(stylename=self.style('table-cell', style))

        if isinstance(value, Formula):
            tc.setAttrNS(TABLENS, 'formula', value.formula)
            tc.setAttrNS(OFFICENS, 'value', str(value.value))
            tc.setAttrNS(OFFICENS, 'value-type', 'float')
            tc.addElement(odf.text.P(text=unicode('0', 'utf-8')))

        elif isinstance(value, HTML):
            tc.setAttrNS(OFFICENS, 'value-type', 'string')
            self._calc.HTML(self._calc._html_parser.parse(value), tc)

        elif isinstance(value, basestring):
            tc.setAttrNS(OFFICENS, 'value-type', 'string')
            tc.addElement(odf.text.P(text=value))

        elif isinstance(value, (float, int)):
            tc.setAttrNS(OFFICENS, 'value-type', 'float')
            tc.setAttrNS(OFFICENS, 'value', str(value))
            tc.addElement(odf.text.P(text=str(value)))

        elif isinstance(value, element.Element):
            tc.setAttrNS(OFFICENS, 'value-type', 'string')
            tc.addElement(value)

        self._cells[cell] = tc

class OpenDocument(object):
    def __init__(self, doc):
        self._doc = doc

        self._styles = {'':{}}

        self.debug = False
        self._html_parser = html5lib.HTMLParser()

        self._style_hr = odf.style.Style(name="Horizontal Rule", family="paragraph")
        self._style_hr.addElement(odf.style.ParagraphProperties(padding="0cm",
                                    borderleft="none", borderright="none", bordertop="none",
                                    borderbottom="0.002cm solid #000000", shadow="none"))
        self._doc.automaticstyles.addElement(self._style_hr)

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

    def P(self, root, p):
        if p is None:
            p = odf.text.P()
            root.addElement(p)
        return p

    def HTML(self, chunk, root, p=None, style={}):
        for child in chunk.childNodes:
            if child.name is None:
                tag = None
            else:
                tag = child.name.lower()
    
            if tag is None:
                if child.value.strip():
                    p = self.P(root, p)
                    if child.value[0].isspace():
                        p.addElement(odf.text.S())
                    s = odf.text.Span(text=child.value.strip(), stylename=self.style('text', style))
                    p.addElement(s)
                    if child.value[-1].isspace():
                        p.addElement(odf.text.S())

            elif tag == 'br':
                p = self.P(root, p)
                p.addElement(odf.text.LineBreak())

            elif tag == 'hr':
                root.addElement(odf.text.P(stylename=self._style_hr))
                p = None

            elif tag in ['p', 'div']:
                if child.attributes.has_key('align'):
                    align = {'right': 'end', 'left': False, 'center': 'center', 'justify': 'justify'}[child.attributes['align']]
                    p = odf.text.P(stylename=self.style('paragraph', {'align': align}))
                else:
                    p = odf.text.P()
                root.addElement(p)
                self.HTML(child, root, p, style)

            elif tag in ['i', 'em']:
                _style = copy.copy(style)
                _style.update({'italic': True})
                self.HTML(child, root, p, _style)

            elif tag in ['b', 'strong']:
                _style = copy.copy(style)
                _style.update({'bold': True})
                self.HTML(child, root, p, _style)

            elif tag == 'u':
                _style = copy.copy(style)
                _style.update({'underline': True})
                self.HTML(child, root, p, _style)

            elif tag == 'strike':
                _style = copy.copy(style)
                _style.update({'strike': True})
                self.HTML(child, root, p, _style)

            elif tag in ['ol', 'ul']:
                self._html_list(child, root, p, style, tag)
                p = None

            elif tag == 'table':
                self._html_table(child, root, p, style)
                p = None

            elif tag in ['html', 'head', 'body', 'tbody', 'tr', 'td']:
                self.HTML(child, root, p, style)

            ## later we'll just ignore what we don't understand, but
            ## right now I want explicit notification.
            else:
                if self.debug: print 'Unexpected tag', tag
                self.HTML(child, root, p, style)
    
        return root

def loadLabels():
    specs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LabelSpecs.pickle')
    f = open(specs)
    l = pickle.load(f)
    f.close()
    return l

class DictObject(object):
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k.replace(' ', '_').replace('.', '_'), v)

class Cards(OpenDocument):
    LABELSPECS = loadLabels()

    @staticmethod
    def addUnit(s):
        return '%f%s' % (s, Cards.LABELSPECS['units'])

    def __init__(self, label):
        super(Cards, self).__init__(opendocument.OpenDocumentText())

        self._label = DictObject(Cards.LABELSPECS['label:' + label])

        self._cards = []

        pl = odf.style.PageLayout(name="pagelayout")

        pl.addElement(odf.style.PageLayoutProperties(
                                            margintop=Cards.addUnit(self._label.top_margin),
                                            marginbottom="0pt",
                                            marginleft=Cards.addUnit(self._label.left_margin),
                                            marginright=Cards.addUnit(self._label.right_margin),
                                            pagewidth=Cards.addUnit(self._label.paper_width),
                                            pageheight=Cards.addUnit(self._label.paper_height),
                                            printorientation="portrait"))
        self._doc.automaticstyles.addElement(pl)

        mp = odf.style.MasterPage(name="Standard", pagelayoutname=pl)
        self._doc.masterstyles.addElement(mp)

        self._layout_table_label_width = odf.style.Style(name="layout table label width", family="table-column")
        self._layout_table_label_width.addElement(odf.style.TableColumnProperties(columnwidth=Cards.addUnit(self._label.width), useoptimalcolumnwidth="false"))
        self._doc.automaticstyles.addElement(self._layout_table_label_width)

        if self._label.width != self._label.horizontal_pitch:
            self._layout_table_horizontal_spacer = odf.style.Style(name="layout table horizontal spacer", family="table-column")
            self._layout_table_horizontal_spacer.addElement(odf.style.TableColumnProperties(columnwidth=Cards.addUnit(self._label.horizontal_pitch - self._label.width), useoptimalcolumnwidth="false"))
            self._doc.automaticstyles.addElement(self._layout_table_horizontal_spacer)

            self._layout_table_colspec = [self._layout_table_label_width, self._layout_table_horizontal_spacer] * self._label.across
            self._layout_table_colspec = self._layout_table_colspec[:-1]
        else:
            self._layout_table_colspec = [self._layout_table_label_width] * self._label.across

        self._layout_table_label_height = odf.style.Style(name="layout table label height", family="table-row")
        self._layout_table_label_height.addElement(odf.style.TableRowProperties(backgroundcolor="#FFFFFF", rowheight=Cards.addUnit(self._label.height), useoptimalrowheight="false"))
        self._doc.automaticstyles.addElement(self._layout_table_label_height)

        if self._label.height != self._label.vertical_pitch:
            self._layout_table_vertical_spacer = odf.style.Style(name="layout table vertical spacer", family="table-column")
            self._layout_table_vertical_spacer.addElement(odf.style.TableRowProperties(rowheight=Cards.addUnit(self._label.vertical_pitch - self._label.height), useoptimalrowheight="false"))
            self._doc.automaticstyles.addElement(self._layout_table_vertical_spacer)

        self._para = odf.style.Style(name="Para", family="paragraph")
        self._para.addElement(odf.style.ParagraphProperties(numberlines="false", linenumber="0"))
        self._para.addElement(odf.style.TextProperties(fontsize="12pt", fontweight="bold"))
        self._doc.automaticstyles.addElement(self._para)

        self._page_break = odf.style.Style(name="table page break", family="table")
        self._page_break.addElement(odf.style.TableProperties(breakafter="true"))
        self._doc.automaticstyles.addElement(self._page_break)

        self._style_card_table_cell = odf.style.Style(name="Card table cell", family="table-cell")
        self._style_card_table_cell.addElement(odf.style.TableCellProperties(padding="0.1cm"))
        self._doc.automaticstyles.addElement(self._style_card_table_cell)

        self._list_style = {}
        for listtype in ('ol', 'ul'):
            self._list_style[listtype] = odf.text.ListStyle(name="HTML list (%s)" % listtype)
            llp = odf.style.ListLevelProperties()
            llp.setAttribute('spacebefore', '0.5cm')
            llp.setAttribute('minlabelwidth', '0.5cm')

            if (listtype == 'ol'):
                lls = odf.text.ListLevelStyleNumber(level=1)
                lls.setAttribute('numsuffix', '.')
                lls.setAttribute('displaylevels', 1)
            else:
                lls = odf.text.ListLevelStyleBullet(level=1, bulletchar=u"•")
                lls.addElement(odf.style.TextProperties(fontname="StarSymbol"))

            lls.addElement( llp )

            self._list_style[listtype].addElement(lls)
            self._doc.automaticstyles.addElement(self._list_style[listtype])

        self._inner_table_style = odf.style.Style(name="Inner table", family="table")
        self._inner_table_style.addElement(odf.style.TableProperties(bordermodel="collapsing"))
        self._doc.automaticstyles.addElement(self._inner_table_style)

        self._inner_table_col_style = odf.style.Style(name="Inner table column", family="table-column")
        self._inner_table_col_style.addElement(odf.style.TableColumnProperties(useoptimalcolumnwidth="true"))
        self._doc.automaticstyles.addElement(self._inner_table_col_style)

        self._inner_table_cell_style = odf.style.Style(name="Inner table cell", family="table-cell")
        self._inner_table_cell_style.addElement(odf.style.TableCellProperties(padding="0.1cm", border="0.02cm solid #000000"))
        self._doc.automaticstyles.addElement(self._inner_table_cell_style)

    def _html_list(self, chunk, root, p, style, listtype):
        l = odf.text.List(stylename=self._list_style[listtype])
        root.addElement(l)
        for li in chunk.childNodes:
            if li.name != 'li':
                continue

            elem = odf.text.ListItem()
            l.addElement(elem)

            self.HTML(li, elem, None, style)

    def _html_table(self, chunk, root, p, style):
        for tbody in chunk.childNodes:
            if tbody.name == 'tbody':
                chunk = tbody
                break

        table = odf.table.Table(stylename=self._inner_table_style)
        root.addElement(table)

        widths = []
        taken = 0
        for tr in chunk.childNodes:
            if tr.name == 'tr':
                for td in tr.childNodes:
                    if td.name == 'td':
                        w = None

                        if td.attributes.has_key('width'):
                            _w = td.attributes['width'].replace(' ', '')
                            if _w.endswith('%'):
                                w = float(_w[:-1])
                                taken += w

                        elif td.attributes.has_key('style'):
                            s = td.attributes['style']
                            for se in s.split(';'):
                                se = se.replace(' ', '')
                                try:
                                    k, v = se.split(':')
                                    if k == 'width' and v.endswith('%'):
                                        w = float(v[:-1])
                                        taken += w
                                        break

                                except ValueError:
                                    pass

                        widths.append(w)
                # we only look at the first row
                break

        if taken > 100:
            raise Exception('Table columns claim %d%%' % taken)

        remaining = 100.0 - taken
        unsized = len(filter(lambda x: not x, widths))
        if unsized:
            remaining = remaining / unsized
            widths = [w or remaining for w in widths]

        for w in widths:
            table.addElement(odf.table.TableColumn(stylename=self.style('table-column', {'columnwidth': '%f%%' % w})))

        for tr in chunk.childNodes:
            if tr.name != 'tr':
                continue

            row = odf.table.TableRow()
            table.addElement(row)

            for td in tr.childNodes:
                if td.name == 'td':
                    tc = odf.table.TableCell(stylename=self._inner_table_cell_style)
                    row.addElement(tc)
                    self.HTML(td, tc, None, style)

    def add(self, card):
        self._cards.append(card.strip())

    def save(self, f):
        cards_per_page = self._label.across * self._label.down
        pages = int(math.ceil(float(len(self._cards)) / cards_per_page))
        spacer = (self._label.width != self._label.horizontal_pitch)

        for page in range(pages):
            table = odf.table.Table(stylename=self._page_break)
            self._doc.text.addElement(table)

            for cs in self._layout_table_colspec:
                table.addElement(odf.table.TableColumn(stylename=cs))

            for row in range(self._label.down):
                data = []
                for col in range(self._label.across):
                    try:
                        data.append(self._cards[(page * cards_per_page) + (col * self._label.down) + row])
                    except IndexError:
                        data.append('')
                    if spacer:
                        data.append('')
                if spacer:
                    data.pop()

                tr = odf.table.TableRow(stylename=self._layout_table_label_height)
                table.addElement(tr)

                for d in data:
                    tc = odf.table.TableCell(stylename=self._style_card_table_cell)
                    tr.addElement(tc)
                    self.HTML(self._html_parser.parse(d), tc)

        self._doc.write(f)

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

    def _html_list(self, chunk, root, p, style, listtype):
        linum = 0
        for li in chunk.childNodes:
            if li.name != 'li':
                continue

            p = self.P(root, None)

            if listtype == 'ul':
                s = odf.text.Span(text='*', stylename=self.style('text', style))
            elif listtype == 'ol':
                linum += 1
                s = odf.text.Span(text='%d.' % linum, stylename=self.style('text', style))
            else:
                raise Exception('List type not set')

            p.addElement(s)
            p.addElement(odf.text.S())
            self.HTML(li, root, p, style)

    def _html_table(self, chunk, root, p, style):
        for tbody in chunk.childNodes:
            if tbody.name == 'tbody':
                chunk = tbody
                break

        for tr in chunk.childNodes:
            if tr.name != 'tr':
                continue

            p = self.P(root, None)

            for td in tr.childNodes:
                if td.name == 'td':
                    self.HTML(td, root, p, style)
                    p.addElement(odf.text.S())

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

