#!/usr/bin/env python
# coding: utf-8

# # MARC I/O functions

# In[3]:


from io import StringIO
import pymarc
from pymarc import Record, marcxml, Field, XMLWriter
# debugging
import pdb
import traceback


# In[1]:


def writeMarcToFile(marcrecs, filename):
    #marcrecs is a list of pymarc record objects
    #writes it as marcXML to filename
    writer = XMLWriter(open(filename, 'wb'))
    for rec in marcrecs:
        writer.write(rec)
    writer.close()

def showMarcRecord(marcrec):
    #prints the value of all fields
    print('000:', marcrec.leader)
    for fld in sorted(marcrec.get_fields(), key=lambda x: x.tag):
        print(fld)

def printFields(records, fldtags):
    #prints the value of the given fields for all records in a set/list
    for rec in records:
        print(rec.get_fields('001')[0])
        for ftag in fldtags:
            if ftag=='000':
                print('\t', ftag, ':', rec.leader)
            elif ftag.startswith('00'):
                for f in rec.get_fields(ftag):
                    print('\t', ftag, ':', f.value())
            else:
                for f in rec.get_fields(ftag):
                    print('\t', ftag, ':', ''.join(f.indicators), f.value())            

def printFieldss(records, fldtags):
    #prints subfieldtags with values of the given fields for all records in a set/list
    for rec in records:
        print(rec.get_fields('001')[0])
        for ftag in fldtags:
            if ftag=='000':
                print('\t', ftag, ':', rec.leader)
            elif ftag.startswith('00'):
                for f in rec.get_fields(ftag):
                    print('\t', ftag, ':', f.value())
            else:
                for f in rec.get_fields(ftag):
                    print('\t', ftag, ':', ''.join(f.indicators), f.subfields)           


# In[ ]:




