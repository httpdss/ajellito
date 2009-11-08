#!/usr/bin/python

import ConfigParser
import urllib
import amara
import sys
import os

iniFile = 'ODTLabels.ini'

fontsize = {
    '145.3': '20',
    '245': '24',
    '45': '7',
    '363': '33',
    '36': '7',
    '96': '12',
    '72': '12',
}

labels = ConfigParser.RawConfigParser()

if os.path.exists(iniFile): labels.read(iniFile)

convert = { '': 1, 'pt': 1, 'mm': 2.8346457, 'in': 72 }

def size(s):
    unit = 'pt'

    if s == '': return '0'

    for u in ['pt', 'mm', 'in']:
        if s.endswith(u):
            s = s[:-len(u)]
            unit = u

    v = ('%f' % float(s)).strip('0')
    if v.endswith('.'): v = v[:-1]
    if v == '': v = '0'
    return v + unit

def fetchLabels(url):
    print 'Fetching %(url)s' % locals()
    data = urllib.urlopen(url)
    doc = amara.parse(data)
    templates = doc.xml_xpath(u'Glabels-templates/Template[Label-rectangle]')
    for template in templates:
        psize = template.size
        if psize == 'US-Letter': psize = 'Letter'
        # section = '%s %s (%s)' % (template.brand, template.part, psize)
        section = ('%s-%s' % (template.brand, template.part)).replace(',', '-').replace(' ', '')
        print section

        if labels.has_section(section):
            if labels.get(section, 'source') == 'glabel': labels.remove_section(section)
            else: continue

        labels.add_section(section)

        try:
            type = template.Meta[0].category
        except AttributeError:
            type = 'label'

        rect = template.Label_rectangle
        layout = rect.Layout
        height = size(rect.height)

        labels.set(section, 'page', psize)
        labels.set(section, 'width', size(rect.width))
        labels.set(section, 'height', height)
        labels.set(section, 'across', layout.nx)
        labels.set(section, 'down', layout.ny)
        labels.set(section, 'top margin', size(layout.y0))
        labels.set(section, 'left margin', size(layout.x0))
        labels.set(section, 'horizontal pitch', size(layout.dx))
        labels.set(section, 'vertical pitch', size(layout.dy))
        labels.set(section, 'source', 'glabel')
        labels.set(section, 'type', type)

        if fontsize.has_key(height):
            labels.set(section, 'font size', fontsize[height])
        else:
            labels.set(section, 'font size', '0')

def fetchPaper(url):
    print 'Fetching %(url)s' % locals()
    data = urllib.urlopen(url)
    doc = amara.parse(data)
    sizes = doc.xml_xpath(u'Glabels-paper-sizes/Paper-size')

    for size in sizes:
        name = size.id
        if name.startswith('US-'): name = name[3:]

        if labels.has_section(name):
            labels.remove_section(name)

        labels.add_section(name)
        labels.set(name, 'width', size.width)
        labels.set(name, 'height', size.height)

for name in ['avery-iso-templates.xml', 'avery-other-templates.xml', 'avery-us-templates.xml', 'brother-other-templates.xml', 'dymo-other-templates.xml', 'misc-iso-templates.xml', 'misc-other-templates.xml', 'misc-us-templates.xml', 'zweckform-iso-templates.xml']:
    fetchLabels('http://git.gnome.org/cgit/glabels/plain/templates/' + name)

fetchPaper('http://git.gnome.org/cgit/glabels/plain/templates/paper-sizes.xml')

labels.write(open(iniFile, 'w'))
