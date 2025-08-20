#!/usr/bin/env python
# coding: utf-8

# # MARC I/O functions

# In[3]:


from io import StringIO
import pymarc
from pymarc import Record, marcxml, Field, XMLWriter, MARCReader
# debugging
import pdb
import traceback



# In[1]:


import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)
import utils
from utils import oneLineStr


# In[3]:


def writeMarcToFile(marcrecs, filename):
    #marcrecs is a list of pymarc record objects
    #writes it as marcXML to filename
    writer = XMLWriter(open(filename, 'wb'))
    for rec in marcrecs:
        writer.write(rec)
    writer.close()

def writeMarcToFileMRC(marcrecs, filename):
    #marcrecs is a list of pymarc record objects
    #writes it as ISO format to filename (.mrc file)
    writer = MARCWriter(open(filename, 'wb'))
    for rec in marcrecs:
        writer.write(rec)
    writer.close()

def readMRC(filename, mode='rb'):
    reader=MARCReader(open(filename, mode=mode))
    recs=[]
    for rec in reader:
        recs.append(rec)
    return recs

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


# In[5]:


#Making spreadsheet reports from marc records based on a spec in form of a dict
#examplespec:{'001':[], '100':['a', 'd'], '245:['a', 'b', 'c']}
#eksempelspek colSpec: {'001':False, '100':True, '245:False}

def colNames (fieldSpec, colSpec):
    #fieldspec is a dict specifying fields and subfields (by their tags) in a report 
    #colSpec is a dict with the same keys as fieldSpec, but with values True or False, indicating whether subfields of the fieldtag 
    #        (fieldSpec[<fieldtag>] are to be listed in separate columns or concatenated into the same column
    #Ex: {'001':[], '245':['a', 'b', 'c']]
    #Returns a tuple of column headings, for the example above: ('f001', 'f245a', 'f245b', 'f245c')
    res=[]
    if set(fieldSpec.keys()) == set(colSpec.keys()):
        for k in fieldSpec.keys():
            if fieldSpec[k]==[] or colSpec[k] is not True:
                res.append('f'+ k)
            else:
                for stag in fieldSpec[k]:
                    res.append('f' + k + stag)
        return tuple(res)

def makeRows4FieldSpec (record, tagSpec, colSpec, rowUnit='001'):
    #tagSpec is a dict with fieldtags as keys, values are a list of subtags, specifying the information to be returned
    #rowUnit indicates the field which occurrences constitute a row/tuple
    #rowUnit='001' implies 1 record per row. 
    #colSpec is a dict with the same keys as tagSpec, but with values True or False, indicating whether subfields of the fieldtag 
    #        (tagSpec[<fieldtag>] are to be listed in separate columns or concatenated into the same column
    #if rowUnit indicates a repeatable field, each occurrence of rowUnit in record constitutes a row. 
    #Values of any other fieldsXsubfiields in tagSpec are concatenated on one row.
    #Returns a list of n tuples (rows) representing record as specified by tagSpec. n is the number of occurrences of rowUnit in record.
    rows=[]  #Number of rows returned
    runit=makeRowPart4Field1(record, rowUnit, tagSpec[rowUnit], concatFields=False) if colSpec[rowUnit] is True else makeRowPart4Field2(record, rowUnit, tagSpec[rowUnit], concatFields=False)
    for i in range(0,len(runit)):
        row=[]
        for k in tagSpec.keys():
            if k!=rowUnit:
                row.extend(makeRowPart4Field1(record, k, tagSpec[k], concatFields=True)) if colSpec[k] is True else row.extend(makeRowPart4Field2(record, k, tagSpec[k], concatFields=True))
            else:
                row.append(runit[i])
        #Each row now contains 1 tuple per fieldtag (tagSpec.keys()).
        ##Make 1 tuple per row
        tpl=[]
        for tp in row:
            tpl+=tp
        rows.append(tuple(tpl))
    return(rows)
    
def makeRowPart4Field1 (record, tg, subtags=[], concatFields=True, sep1='|', sep2='$'):
    #Returns a list of tuples, each a tuple of subfield values for field tg and subfield subtags
    #If tg occurs >1 in record create a row for each occurrence if concatFields=False
    #if concatFields=True: Cncatenate all occurrences of tg
    #if any subfield occurrs >1, always concatenate the values
    #Similar to makeRowPart4Field2, to be used when subfields are listed in separate columns
    tuples=[]
    if record.get_fields(tg) == []:
        tuples=['']
        if subtags != []:
            tuples*=len(subtags)     #Fyll opp med tomme strenger for hvert delfelt
        tuples=[tuple(tuples)]
    elif concatFields is True:       
        valstr=''    #if no subfieldtags
        subdict=dict()    #if subfieldtags
        for subtag in subtags:
            subdict[subtag]=''
        for fld in record.get_fields(tg):
            if subtags==[]:
                if tg.startswith('00'):
                    valstr= valstr + sep1 + fld.value()
                else:
                    valstr= valstr + sep1 + oneLineStr(fld.value())
            else:
                for subtag in subtags:
                    substr=''
                    for subfld in fld.get_subfields(subtag):
                        substr= substr + sep2 + oneLineStr(subfld)
                    subdict[subtag]=subdict[subtag]+sep1 +substr.strip(sep2)
        if valstr !='':
            tuples.append((valstr.strip(sep1).strip(sep2),))
        else:
            for k in subdict.keys():
                tuples.append(subdict[k].strip(sep1).strip(sep2))
            tuples=[tuple(tuples)]
    else:
        for fld in record.get_fields(tg):
            fieldval=[]
            if subtags==[]:
                if tg.startswith('00'):
                    fieldval.append(fld.value())   #we want the exact string for positional fields
                else:
                    fieldval.append(oneLineStr(fld.value()))
            else:
                for subtag in subtags:
                    substr=''
                    for subfld in fld.get_subfields(subtag):
                        substr= substr + sep2 + oneLineStr(subfld)
                    fieldval.append(substr.strip(sep2))
                #print(fieldval)
            tuples.append(tuple(fieldval))
    return tuples

def makeRowPart4Field2 (record, tg, subtags=[], concatFields=True, sep1='|', sep2='$'):
    #Returns a list of tuples/rows, each a tuple of one string, consisting of the value of tg as specified by subtags
    #If tg occurs >1 in record create a row for each occurrence if concatFields=False
    #if concatFields=True: Cncatenate all occurrences of tg
    #Similar to makeRowPart4Field2, to be used when 1 column per field
    tuples=[]
    if record.get_fields(tg) == []:
        tuples.append(('',))
    elif concatFields is True:
        valstr=''    #if no subfieldtags
        subfldstr=''    #if subfieldtags
        for fld in record.get_fields(tg):
            if subtags==[]:
                if tg.startswith('00'):
                    valstr= valstr + sep1 + fld.value()   #we want the exact string for positional fields
                else:
                    valstr= valstr + sep1 + oneLineStr(fld.value())
            else:
                for subtag in subtags:
                    substr=''   #i tilfelle flere forekomster av subfield
                    for subfld in fld.get_subfields(subtag):
                        substr= substr + sep2 + oneLineStr(subfld)
                    valstr= valstr + ' ' + substr.strip(sep2)   #Just space as separator between subfields of same field
                valstr=valstr+sep1
        tuples.append((valstr.strip(sep1).strip(sep2),))
    else:
        for fld in record.get_fields(tg):
            fieldval=[]
            if subtags==[]:
                if tg.startswith('00'):
                    fieldval.append(fld.value())   #we want the exact string for positional fields
                else:
                    fieldval.append(oneLineStr(fld.value()))
            else:
                valstr=''
                for subtag in subtags:
                    substr=''
                    for subfld in fld.get_subfields(subtag):
                        substr= substr + sep2 + oneLineStr(subfld)
                    valstr= valstr + ' ' + substr.strip(sep2)   #Just space as separator between subfields of same field
                fieldval.append(oneLineStr(valstr.strip(sep2)))
            tuples.append(tuple(fieldval))
    return tuples


# In[ ]:




