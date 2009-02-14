#!/usr/bin/python

import ConfigParser
import os
import zipfile
import sys
import xml.dom.minidom
import cStringIO
import types
import decimal
import htmllib, formatter

class ODTLabels:
    UNITS = 'in'
    nsStyle = 'urn:oasis:names:tc:opendocument:xmlns:style:1.0'
    nsFO = 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0'
    nsDraw = 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0'
    nsSVG = 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0'
    nsText = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
    nsTable = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    nsOffice = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    
    def __init__(self, iniFile = __file__.replace('.py', '.ini')):
        self.labels = ConfigParser.RawConfigParser()
        if os.path.exists(iniFile): self.labels.read(iniFile)

    def setSheetType(self, st):
        self.st = st

        for k, v in self.labels.items(st):
            if k in ['width', 'height', 'left margin', 'top margin', 'vertical pitch', 'horizontal pitch']:
                v = self.standardSize(v)
            if k in ['across', 'down']:
                v = int(v)
            if k == 'page':
                k = 'papersize'
            k = k.replace(' ', '_')
            setattr(self, k, v)

        for k, v in self.labels.items(self.papersize):
            setattr(self, 'page_' + k, self.sizeStr(self.standardSize(v)))

    def setTemplate(self, odt):
        self.srcODT = odt

    def toString(self, v):
        tpe = type(v)

        if tpe in [types.NoneType]:
            v = u''
        if tpe in [types.IntType, types.FloatType, decimal.Decimal]:
            v = unicode(str(v))
        elif isinstance(v, types.StringTypes):
            try:
                vd = unicode(v).decode('utf-8')
            except:
                vd = v.encode('ascii', 'ignore')
                vd = unicode(vd).decode('utf-8')
            f = cStringIO.StringIO()
            wr = formatter.DumbWriter(f)
            fmt = formatter.AbstractFormatter(wr)
            p = htmllib.HTMLParser(fmt)
            p.feed(vd)
            p.close()
            v = f.getvalue()
        else:
            raise Exception(tpe)

        try:
            return unicode(v).decode('utf-8')
        except:
            v_a = v.decode('ascii', 'ignore')
            return unicode(v_a).decode('utf-8')

    def makeLabels(self, tasks, stories, output):
        odtinput = zipfile.ZipFile(self.srcODT)
        odtoutput = zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED)
        #odtoutput = file(output, 'w')

        #zipdata = []
        for name in odtinput.namelist():
            if name.endswith('/'):
                dir = zipfile.ZipInfo(name)
                odtoutput.writestr(dir, '')
            elif name == 'styles.xml':
                odtoutput.writestr(name, self._setPageSize(odtinput.read(name)))
                #zipdata.append((None, name, self._setPageSize(odtinput.read(name))))
            elif name == 'content.xml':
                odtoutput.writestr(name, self._makeLabels(odtinput.read(name), tasks, stories))
                #zipdata.append((None, name, self._makeLabels(odtinput.read(name), tasks, stories)))
            else:
                odtoutput.writestr(name, odtinput.read(name))
                #zipdata.append((None, name, odtinput.read(name)))
        #mkzip.create_zip(odtoutput, zipdata )
        odtinput.close()
        odtoutput.close()

    def standardSize(self, s):
        convert = { 'pt': {'pt': 1, 'mm': 2.8346457, 'in': 72 },
                    'cm': {'pt': 0.035277778, 'mm': 0.1, 'in': 2.54 },
                    'in': {'pt': 0.013888889, 'mm': 0.039370079, 'in': 1 }
                }
        unit = 'pt' # assumed unit when none specified

        if s == '': return '0'

        for u in ['pt', 'mm', 'in']:
            if s.endswith(u):
                s = s[:-len(u)]
                unit = u
        return float(s) * convert[ODTLabels.UNITS][unit]

    def sizeStr(self, s):
        s = ('%.4f' % s).rstrip('0')
        if s[-1] == '.': s = s[:-1]
        return (s + ODTLabels.UNITS).decode('utf-8')


    def _setPageSize(self, xmldata):
        input = cStringIO.StringIO(xmldata)
        styles = xml.dom.minidom.parse(input)
        for p in styles.getElementsByTagNameNS(ODTLabels.nsStyle, 'page-layout-properties'):
            p.setAttributeNS(ODTLabels.nsFO, u'fo:page-height', self.page_height.decode('utf-8'))
            p.setAttributeNS(ODTLabels.nsFO, u'fo:page-width', self.page_width.decode('utf-8'))
            p.setAttributeNS(ODTLabels.nsFO, u'fo:margin-bottom', self.sizeStr(0))
            p.setAttributeNS(ODTLabels.nsFO, u'fo:margin-top', self.sizeStr(0))
            p.setAttributeNS(ODTLabels.nsFO, u'fo:margin-left', self.sizeStr(0))
            p.setAttributeNS(ODTLabels.nsFO, u'fo:margin-right', self.sizeStr(0))
        input.close()
        return styles.toxml('utf-8')

    def _makeLabels(self, xmldata, tasks, stories):
        input = cStringIO.StringIO(xmldata)
        content = xml.dom.minidom.parse(input)
        frames = content.getElementsByTagNameNS(ODTLabels.nsDraw, 'frame')
        taskTemplate = None
        storyTemplate = None
        for frame in frames:
            name = frame.getAttributeNS(ODTLabels.nsDraw, 'name')
            if name == 'Task':
                taskTemplate = frame
            elif name == 'Story':
                storyTemplate = frame
            else:
                frame.parentNode.removeChild(frame)
                frame.unlink()
                pass
    
        if taskTemplate is None and storyTemplate is None:
            return content.toxml('utf-8')

        for template in [taskTemplate, storyTemplate]:
            if template is None: continue

            for sibling in template.parentNode.childNodes:
                if sibling.nodeName == 'text:p':
                    sibling.parentNode.removeChild(sibling)
                    sibling.unlink()

        for template in [taskTemplate, storyTemplate]:
            if template is None: continue

            for text in template.getElementsByTagNameNS(ODTLabels.nsDraw, 'text-box'):
                try:
                    text.removeAttributeNS(ODTLabels.nsFO, 'min-height')
                except xml.dom.NotFoundErr:
                    pass

            template.setAttributeNS(ODTLabels.nsSVG, u'svg:width', self.sizeStr(self.width))
            template.setAttributeNS(ODTLabels.nsSVG, u'svg:height', self.sizeStr(self.height))
            template.setAttributeNS(ODTLabels.nsText, u'text:anchor-type', u'page')

            style_name = template.getAttributeNS(ODTLabels.nsDraw, 'style-name')
            framestyles = content.getElementsByTagNameNS(ODTLabels.nsStyle, 'style')
            for style in framestyles:
                sn = style.getAttributeNS(ODTLabels.nsStyle, 'name')
                if sn == style_name:
                    for gp in style.getElementsByTagNameNS(ODTLabels.nsStyle, 'graphic-properties'):
                        gp.setAttributeNS(ODTLabels.nsStyle, u'style:protect', u'size')

        pagebreak = content.createElementNS(ODTLabels.nsStyle, u'style')
        pagebreak.setAttributeNS(ODTLabels.nsStyle, u'style:name', u'pagebreak')
        pagebreak.setAttributeNS(ODTLabels.nsStyle, u'style:family', u'paragraph')
        pagebreak.setAttributeNS(ODTLabels.nsStyle, u'style:parent-style-name', u'Standard')
        spp = content.createElementNS(ODTLabels.nsStyle, u'paragraph-properties')
        spp.setAttributeNS(ODTLabels.nsFO, u'fo:break-before', u'page')
        pagebreak.appendChild(spp)

        for oaa in content.getElementsByTagNameNS(ODTLabels.nsOffice, 'automatic-styles'):
            oaa.appendChild(pagebreak)
            break
            
        cpp = self.down * self.across

        for card in tasks: card['_template'] = taskTemplate
        for card in stories: card['_template'] = storyTemplate

        for cardID, label in enumerate(stories + tasks):
            page = cardID / cpp
            col = cardID % self.across
            row = (cardID /self.across) % self.down

            template = label['_template']

            if cardID != 0 and cardID % cpp == 0:
                #<text:p text:style-name="Standard"/><text:p text:style-name="pagebreak"/>
                pagebreak = content.createElementNS(ODTLabels.nsText, u'p')
                pagebreak.setAttributeNS(ODTLabels.nsText, u'text:style', u'pagebreak')
                template.parentNode.appendChild(pagebreak)

            card = template.cloneNode(True)

            for table in card.getElementsByTagNameNS(ODTLabels.nsTable, 'table'):
                table.setAttributeNS(ODTLabels.nsTable, u'table:name', u'table-%d' % cardID)

            card.setAttributeNS(ODTLabels.nsDraw, u'draw:name', u'card-%d' % cardID)
            card.setAttributeNS(ODTLabels.nsDraw, u'draw:z-index', u'%d' % cardID)
            card.setAttributeNS(ODTLabels.nsSVG, u'svg:x', self.sizeStr((self.left_margin + col * self.horizontal_pitch)))
            card.setAttributeNS(ODTLabels.nsSVG, u'svg:y', self.sizeStr((self.top_margin + row * self.vertical_pitch)))
            card.setAttributeNS(ODTLabels.nsText, u'text:anchor-page-number', str(page + 1))

            for var in card.getElementsByTagNameNS(ODTLabels.nsText, 'variable-set'):
                varname = var.getAttributeNS(ODTLabels.nsText, 'name')
                if label.has_key(varname):
                    v = label[varname]
                else:
                    v = ''

                subst = content.createTextNode(self.toString(v))
                var.parentNode.replaceChild(subst, var)
                var.unlink()

            template.parentNode.appendChild(card)

        for template in [taskTemplate, storyTemplate]:
            if template:
                template.parentNode.removeChild(template)
                template.unlink()

        input.close()
        return content.toxml('utf-8')

if __name__ == "__main__":
    labels = ODTLabels()
    labels.setSheetType('Hema-Etiketten')
    labels.setTemplate('template.odt')

    data = [{'TaskID': str(c)} for c in range(30)]
    labels.makeLabels(data, open('merged.odt', 'w'))
