#!/usr/bin/python

import ConfigParser
import urllib
import amara
import sys
import os

try:
    import cPickle as pickle
except ImportError:
    import pickle

iniFile = 'LabelSpecs.ini'

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
        section = ('label:%s-%s' % (template.brand, template.part)).replace(',', '-').replace(' ', '')
        print section

        if not labels.has_section('paper:' + psize):
            print 'Skipping label "%s" with unknown paper size "%s"' % (section, psize)
            continue

        if labels.has_section(section):
            if labels.get(section, 'source') == 'glabel': labels.remove_section(section)
            else: continue

        labels.add_section(section)

        rect = template.Label_rectangle
        layout = rect.Layout
        height = size(rect.height)

        labels.set(section, 'paper', psize)
        labels.set(section, 'width', size(rect.width))
        labels.set(section, 'height', height)
        labels.set(section, 'across', layout.nx)
        labels.set(section, 'down', layout.ny)
        labels.set(section, 'top margin', size(layout.y0))
        labels.set(section, 'left margin', size(layout.x0))
        labels.set(section, 'horizontal pitch', size(layout.dx))
        labels.set(section, 'vertical pitch', size(layout.dy))
        labels.set(section, 'source', 'glabel')

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

        name = 'paper:%s' % name

        if labels.has_section(name):
            labels.remove_section(name)

        labels.add_section(name)
        labels.set(name, 'width', size.width)
        labels.set(name, 'height', size.height)

fetchPaper('http://git.gnome.org/cgit/glabels/plain/templates/paper-sizes.xml')

for name in ['avery-iso-templates.xml', 'avery-other-templates.xml', 'avery-us-templates.xml', 'brother-other-templates.xml', 'dymo-other-templates.xml', 'misc-iso-templates.xml', 'misc-other-templates.xml', 'misc-us-templates.xml', 'zweckform-iso-templates.xml']:
    fetchLabels('http://git.gnome.org/cgit/glabels/plain/templates/' + name)


sections = list(labels.sections())
papersizes = []
labelspecs = []

for section in sections:
    if section.startswith('paper:'):
        papersizes.append(section)
        continue

    if section.startswith('label:'):
        if not labels.has_section('paper:' + labels.get(section, 'paper')):
            raise Exception(section + ' has unknown paper size ' + labels.get(section, 'paper'))

        labelspecs.append(section)
        continue
    
    labels.remove_section(section)

labels.write(open(iniFile, 'w'))

dump = {'units': 'cm', 'papersizes': {}, 'labels': []}

def standardSize(s):
    convert_to = { 'pt': {'pt': 1, 'mm': 2.8346457, 'in': 72 },
                'cm': {'pt': 0.035277778, 'mm': 0.1, 'in': 2.54 },
                'in': {'pt': 0.013888889, 'mm': 0.039370079, 'in': 1 }
            }
    unit = 'pt' # assumed unit when none specified

    if s == '': return '0'

    for u in ['pt', 'mm', 'in']:
        if s.endswith(u):
            s = s[:-len(u)]
            unit = u

    return float(s) * convert_to[dump['units']][unit]

for psize in papersizes:
    name = psize[len('paper:'):]
    dump['papersizes'][name] = []

    dump[psize] = {'width': standardSize(labels.get(psize, 'width')), 'height': standardSize(labels.get(psize, 'height'))}

def margin(page, mrg, label, pitch, n):
    m = page
    m -= mrg
    m -= label
    m -= pitch * (n-1)
    return m

for label in labelspecs:
    name = label[len('label:'):]
    dump['papersizes'][labels.get(label, 'paper')].append(name)
    dump['labels'].append(name)

    dump[label] = {}
    for prop in ('paper',):
        dump[label][prop] = labels.get(label, prop)

    for prop in ('width', 'height', 'top margin', 'left margin', 'horizontal pitch', 'vertical pitch'):
        dump[label][prop] = standardSize(labels.get(label, prop))

    for prop in ('across', 'down'):
        dump[label][prop] = int(labels.get(label, prop))

    for prop in ('height', 'width'):
        dump[label]['paper.' + prop] = dump['paper:' + dump[label]['paper']][prop]

    l = dump[label]
    dump[label]['right margin'] = margin(l['paper.width'], l['left margin'], l['width'], l['horizontal pitch'], l['across'])
    dump[label]['bottom margin'] = margin(l['paper.height'], l['top margin'], l['height'], l['vertical pitch'], l['down'])

f = open('LabelSpecs.pickle', 'wb')
pickle.dump(dump, f)
f.close()
