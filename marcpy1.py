#!/usr/bin/env python
# coding: utf-8

# # Functions for Marc handling - 1
# 

# In[1]:


from pprint import pprint as pp
import re #regular expressions
import requests
#import urllib, urllib.parse     # used for percent-encoding strings
#import xml
#from xml import etree
#from xml.etree import ElementTree
from io import StringIO
import pymarc
from pymarc import Record, marcxml, Field, XMLWriter
from collections import Counter
import csv
import difflib
from difflib import SequenceMatcher
import itertools
import numpy
import unicodedata as ucd
# debugging
import pdb
import traceback

#local modules on git tkpy
import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)

import utils
from utils import trim
#import iomarc
#import iogeneral


# In[2]:


from pymarc import Record, marcxml, Field
from collections import Counter
def fieldCounter(records):
    #calculates the occurrences of all marc fields present in records
    #records is a list of pymarc.Record objects
    #returns a Counter object
    cnt=Counter()
    fields=[]
    tags=[]
    for rec in records:
        fields.extend(rec.get_fields())  #extract all fields 
    for fld in fields:
        tags.append(fld.tag)
    for tag in sorted(tags):
        cnt[tag] +=1
    return cnt

def subfieldCounter(records, fieldtags, subfieldtags, delimiter='$'):
    #calculates the occurrences of the subfields given by fieldtags and subfieldtags
    #Example: If fieldtags=['100', '700'], subfieldtags=['e', '4'], the number of occurrences of
    #         100$e, 100$4, 700$e and 700$4 are counted
    #records is a list of pymarc.Record objects
    #returns a Counter object
    cnt=Counter()
    fields=[]
    tags=[]
    for rec in records:
        fields.extend(rec.get_fields(*fieldtags))  #extract all fields correspnding to fieldtags
    for fld in fields:
        for sfldtag in subfieldtags:                #check if the given subfields exist in fld
            if len(fld.get_subfields(sfldtag))>0:
                tags.append(fld.tag + delimiter + sfldtag)
    for tag in tags:
        cnt[tag] +=1
    return cnt

def subfieldCounter2(records, delimiter='$'):
    #calculates the occurrences of all subfields in all fields in records.
    #Also erroneous tags are counted
    #records is a list of pymarc.Record objects
    #returns a Counter object
    #Multiple occurrences of a subfield are counted according to occurrence
    fieldtags=[]
    #Do not consider control fields
    for tg in list(fieldCounter(records).keys()):
        if not tg.startswith('00'):
            fieldtags.append(tg)
    cnt=Counter()
    fields=[]
    tags=[]
    for rec in records:
        fields.extend(rec.get_fields(*fieldtags))  #extract all fields correspnding to fieldtags
    for fld in fields:
        sublist=fld.subfields   # e.g. ['a','Haugianismen','b','dens Historie og Væsen, 'b', 'samt Forhold til Herrnhuttismen']
        subfieldtags=[]
        for i in range(0, len(sublist)//2):
            j=i*2
            subfieldtags.append(sublist[j])       #e.g. ['a', 'b', 'b', 'c']   ('b' is repeated)
        for sfldtag in subfieldtags:                #check if the given subfields exist in fld
            #if len(fld.get_subfields(sfldtag))>1:
                #print(fld.get_subfields(sfldtag))
            if len(fld.get_subfields(sfldtag))>0:
                tags.append(fld.tag + delimiter + sfldtag)
    for tag in tags:
        cnt[tag] +=1
    return cnt

def valueCounter(records, fieldtags, subfieldtags=None, fldPart=None, slice=None, 
                 separateCounting=False, delimiter='$', leadertag='000', countDupl=True):
    #***UPDATED 26.04.2022***** (configure counting of duplicate values)
    #calculates the occurrences of different values the fields, subfields or slice of a controlfield or leader
    #If fldPart is not None, but a nonempty numeric tuple, only the corresponding part of the value is considered
    #fldPart is not considered if >1 subfields and separateCounting ==False
    #subfields given by fieldtags and subfieldtags. Leader encoded by fieldtag leadertag
    #Example: If fieldtags=['100', '700'], subfieldtags=['e', '4'], and separateCounting is True,
    #         the number of value occurrences of 100$e, 100$4, 700$e and 700$4 separately are counted
    #         If separateCounting is False, the number of value occurrences of 100$e$4 and 700$e$4 
    #         delimited by delimiter are counted                        
    #         If subfieldtags and slice are not given, field.value() is used for coounting
    #Example2: Fieldldtags=['651'] and subliedtags=['a']. If countDupl=False, then the same value of 
    #           651a within the same record is counted only once, hence the fields 
    #          651$aUSA$2noram and 651$aUSA$2humord  in the same record count as 1 value in this case.
    #records is a list of pymarc.Record objects
    #returns a Counter object
    cnt=Counter()
    #fields=[]
    allvalues=[]
    #Get all field objects
    for rec in records:
        values=[]
        if leadertag in fieldtags:
            if slice in [None, ()]:
                values.append(rec.leader)    #slice None or empty
            elif len(slice)>1: 
                values.append(rec.leader[slice[0]:slice[1]])
            else:
                values.append(rec.leader[slice[0]:])
        for fld in rec.get_fields(*fieldtags):          #alle strenger som ikke er feltkode blir ignorert
                #fld a Controlfield?
            if fld.tag in ['001', '003', '005', '006', '007', '008']:
                if slice in [None, ()]:
                    values.append(fld.value())    #slice None or empty
                elif len(slice)>1: 
                    values.append(fld.value()[slice[0]:slice[1]])
                else:
                    values.append(fld.value()[slice[0]:])     
            elif subfieldtags in [None, []]:
                if fldPart in [None, ()]:
                    values.append(fld.value())
                elif len(fldPart)>1:
                    values.append(fld.value()[fldPart[0]:fldPart[1]])
                else:
                    values.append(fld.value()[fldPart[0]:])
            elif len(subfieldtags)>1 and separateCounting==False:
                svals=fld.get_subfields(*subfieldtags)           #list of subfield values
                values.append(delimiter.join(svals))
            else:                                  #len(subfieldtag)<=1 or separateCounting=True
                for sfldtag in subfieldtags:
                    svals=fld.get_subfields(sfldtag)
                    for v in svals:
                        if fldPart in [None, ()]:
                            values.append(v)
                        elif len(fldPart)>1:
                            values.append(v[fldPart[0]:fldPart[1]])
                        else:
                            values.append(v[fldPart[0]:])
        #Should internal duplicates count?
        if countDupl:
            allvalues.extend(values)
        else:
            allvalues.extend(list(set(values)))
    for val in sorted(allvalues):
        cnt[val] +=1
    return cnt

def fieldExtractor(records, fieldtags):
    #returns a list of field values corresponding to the tags in fieldtags
    #records is a list of pymarc.Record objects
    #Example: fieldExtractor(solstad, ['913']) returns (1 record per line)
    #[['913: Solstad NB'],
    # ['913: Solstad NB', '913: Littforsk NB'],
    # ['913: Solstad NB'],
    # ['913: Solstad NB', '913: Littforsk NB'],
    # ['913: Solstad NB'],...
    #]
    result = []
    for rec in records:
        fields= rec.get_fields(*fieldtags)
        fieldValues=[]
        for fld in fields:
            fieldValues.append(fld.tag + ': ' + fld.value())
        result.append(fieldValues)
    return result

def fieldExtractorCondensed(records, fieldtags):
    #returns a list of lists of field values corresponding to the tags in fieldtags
    #records is a list of pymarc.Record objects
    #only records with value on at least one of the fields in fieldtags are represented in the list
    result = []
    for rec in records:
        fields= rec.get_fields(*fieldtags)
        fieldValues=[]
        for fld in fields:
            if fld.value()!= '':
                fieldValues.append(fld.tag + ': ' + fld.value())
        if fieldValues != []:
            result.append(fieldValues)
    return result

def fieldExtractorAsDict(records, fieldtags, IDfieldtag):
    #returns a dict in which the 
    #      keys are the field value of IDfieldtag NOTE: Uniqueness and of IDfieldtag is assumed
    #      values are a list of values of all subfields in the fields repr by fieldtags 
    #records is a list of pymarc.Record objects
    result = dict()
    for rec in records:
        k=rec.get_fields(IDfieldtag)[0].value()
        fields= rec.get_fields(*fieldtags)
        fieldValues=[]
        for fld in fields:
            if fld.value()!= '':
                fieldValues.append(fld.tag + ': ' + fld.value())
        if fieldValues != []: 
            result[k]=fieldValues
    return result

def fieldObjectExtractor(records, fieldtags):
    #returns a list lists of pymarc.field objects corresponding to the tags in fieldtags
    #records is a list of pymarc.Record objects
    result = []
    for rec in records:
        fields= rec.get_fields(*fieldtags)
        result.extend(fields)
    return result

def subfieldExtractor(records, fieldtag, subfieldtags):
    #returns a list of subfield values corresponding to the subfieldtags in fieldtag
    #records is a list of pymarc.Record objects
    #Example: subfieldExtractor(solstad, '913',['a','b']) returns (1 record per line)
    #[[['Solstad', 'NB']],
    # [['Solstad', 'NB'], ['Littforsk', 'NB']],
    # [['Solstad', 'NB']],
    # [['Solstad', 'NB'], ['Littforsk', 'NB']],
    # [['Solstad', 'NB']],...
    #]
    result = []
    for rec in records:
        fields= rec.get_fields(fieldtag)   #note: fieldtag may be repeatable
        fieldValues=[]
        for fld in fields:
            fieldValues.append(fld.get_subfields(*subfieldtags))
        result.append(fieldValues)
    return result

def subfieldExtractor2(fields, subfieldtags):
    #returns a list of values of subfieldtags
    #fields is a list of pymarc.field objects
    result = []
    for fld in fields:
        subflds=fld.get_subfields(*subfieldtags)
        result.extend(subflds)
    return result

def fieldValues (records, fieldtags , slice=None):
    #returns a set containing all the different values of the fields specified
    #records is a list of pymarc.Record objects
    #Example: fieldValues(solstad, ['913']) returns
    #{'solstad', 'littforsk'}
    # slice is meant to denote the part to extract from control (position based) fields
    #       should be given as a tuple
    values = []
    for rec in records:
        fields= rec.get_fields(*fieldtags)   
        for fld in fields:
            if slice is None:
                values.append(fld.value())
            elif isinstance(slice, tuple):
                values.append(fld.value()[slice[0]:slice[1]])
    return set(values)

def leaderValues (records, slice=None):
    #returns a set containing all the different values of the specified positions of leader
    #records is a list of pymarc.Record objects
    #Example: fieldValues(solstad, ['913']) returns
    # slice is a tuple indicating the part to extract from leader
    # if slice is None, the whole leader is extracted
    values = []
    for rec in records:
        ldr= rec.leader
        if slice is None:
            values.append(ldr)
        elif isinstance(slice, tuple):
            values.append(ldr[slice[0]:slice[1]])
    return set(values)

def subfieldValues (records, fieldtags, subfieldtags):
    #returns a set containing all the different values of the fields/subfields specified
    #records is a list of pymarc.Record objects
    #Example: subfieldValues(solstad, ['913'],['a','b']) returns
    #{'solstad', 'littforsk', 'NB'}
    values = []
    for rec in records:
        fields= rec.get_fields(*fieldtags)   
        for fld in fields:
            values.extend(fld.get_subfields(*subfieldtags))
    return set(values)

def subfieldValueTuples (records, fieldtags, subfieldtags, includeId=True):
    #returns a set containing all the different tuples of the fields/subfields specified
    #The tuples have the same length and order as subfieldtags
    #records is a list of pymarc.Record objects
    #Example: subfieldValues(solstad, ['913'],['a','b']) returns
    #{('solstad', 'NB'), ('littforsk', 'NB')}
    #if a subfield does not exist, an empty string will be put in the tuple
    values = []
    for rec in records:
        fields= rec.get_fields(*fieldtags)   
        for fld in fields:
            slist=[]
            if fld.is_control_field():
                val=fld.value()
                if val=='':
                    slist.append(())
                else:
                    slist.append(tuple([val]))    #singleton tuple
                #print(slist)
            else:
                for sfld in subfieldtags:             #iterate over subfieldtags to be sure of order
                    svals=fld.get_subfields(sfld)
                    if svals ==[]:
                        slist.append(())
                    else:
                        slist.append(tuple(svals))
                #print(slist)
            if includeId==True:
                slist.insert(0, tuple([rec.get_fields('001')[0].value()]))   #singleton tuple
                #print(slist)
            values.append(tuple(slist))
    return set(values)


def writeFieldsToCSV(filename, records, fieldtags, condense=False):
    #write the value of the fields specified in fieldtags to the file filename (should be a .csv or excel(?)file)
    with open(filename, 'w', newline='',  encoding = 'utf-8') as f:
        thiswriter=csv.writer(f, delimiter= '|',)
        if condense:
            thiswriter.writerows(fieldExtractorCondensed(records, fieldtags))
        else: 
            thiswriter.writerows(fieldExtractor(records, fieldtags)) 
        f.close()
        
def writeSubfieldsToCSV(filename, records, fieldtag, subfieldtags):
    #write the value of the fields specified in fieldtags to the file filename (should be a .csv or excel(?)file)
    with open(filename, 'w', newline='',  encoding = 'utf-8') as f:
        thiswriter=csv.writer(f, delimiter= '|',)
        subfieldvals=subfieldExtractor(records, fieldtag, subfieldtags) 
        for rowlist in subfieldvals:            #rowlist is on the form [['Solstad', 'NB'], ['Littforsk', 'NB'], ...]
            thiswriter.writerow(itertools.chain(*rowlist))
        f.close()

def writeFieldDictToCSV(filename, records, fieldtags, IDfieldTag):
    #write the value of IDfieldTag and ditto of the fields specified in fieldtags to the file filename (should be a .csv or excel(?)file)
    #Only records for which at least one of the fields in fieldtags ahs value are represented in the list 
    #(assume that all records have value for IDfieldTag)
    # Example dict: 
    #   {'9500002': ['505: Biblioteket har: [Årg. 1] (1995)-', '505: ISSN 0806-2218'],
    #    '9500045': ['500: Forfatter av b. 7: Ådne Fardal Klev',
    #                '505: B.1. Lyngdal I : vestre del : gard og folk. - 599 s. - NLI 6858',
    #                '505: B.2. Lyngdal II : midtre del : gard og folk. - 737 s. - NLI 6788']
    #   }            
    with open(filename, 'w', newline='',  encoding = 'utf-8') as f:
        thiswriter=csv.writer(f, delimiter= '|',)
        fieldDict=fieldExtractorAsDict(records, fieldtags, IDfieldTag)
        for itm in fieldDict.items():
            thiswriter.writerow([itm[0]])
            for i in itm[1]:
                #print(i)
                thiswriter.writerow(['',trim(i)])
        f.close()
        

#Defines Work as subclass of pymarc.Record
class Work(pymarc.Record):
    def addManifestation(self, record):
        self.manifestations.append(record)
    
    def getManifestations(self):
        return self.manifestations
    
    def setPreferredTitle(self, title):
        fld=Field('245', indicators=['1', ' '], subfields=['a', title, 'a', 'hei'])
        self.add_field(fld)

#Not finished!!    
#bruke difflib.get_close_matches??
def findSimilarRecords(records, record, compareDict, strict=False):
    #returns a list of records in records similar to record
    #when comparing the tags given in compareDict
    #compareDict is on the form: {fieldtag1:[subfieldtag1, subfieldtag2,...], fieldtag2 : [subfieldtag3, subfieldtag4,...]}
    #if strict is True, exact equality is required
    result = []
    #tags=compareDict.keys()
    # specify values to compare from record
    for tag in iter(compareDict):
        subfields=compareDict[tag]
        flds1=record.get_fields(tag)

    for rec in records:
        for tag in tags:
            subfields=compareDict[tag]
            flds2=rec.get_fields(tag)
            for fld in subfields:
                x=True
    return True
 
def fieldValue(field, subfieldTags):
    #Returns a the field value as a string consitutesd of the values of those of its subfield given by subfieldTags
    #Essentialy the same as field.get_fields(*subfieldTags), but returns a string instead of a list of strings
    valus=field.get_subfields(*subfieldTags)
    #insert spaces between subfield values
    if len(valus) > 1:
        valus2=[valus[0]]  
        for i in range(1,len(valus)):
            valus2.extend([' ', valus[i]])
    else:
        valus2=valus
    return ''.join(valus2)
    
def workKey(record, fieldSpec):
    #returns a tuple of strings based on the fields and subfields specified in fieldSpec (a list of 3-tuples)
    # on the form: [(fieldtag1,occnum,[subfieldtag1, subfieldtag2,...]), (fieldtag2, occnum, [subfieldtag3, subfieldtag4,...]),...]
    #the resulting tuple has 1 item per 3-tuple in fieldSpec
    
    #if the list of subfieldtags is empty, all subfields are included
    #if occnum=<0, the each occurrence  is appended to the resulting tuple
    #if occnum >=0, only tje designated occurrence is used
    
    wKey = ()
    for tpl in fieldSpec:
        if tpl[1] < 0:                           #append all occurrences into this key
            for fld in record.get_fields(tpl[0]):
                if tpl[2] == []:
                    wKey= wKey + (fld.value(),)
                else:
                    wKey= wKey + (fieldValue(fld, tpl[2]),)
        else:
            fld= record.get_fields(tpl[0])[tpl[1]]   #use only the occurrence given by tpl[1]
            if tpl[2] == []:
                wKey= wKey + (fld.value(),)
            else:
                wKey= wKey + (fieldValue(fld, tpl[2]),)
    return wKey

def assignWorkKey(record, keytuple):
    #assign the keytuple to field '9xx' and subfields '1', '2', etc
    subflds = []
    for n in range(len(keytuple)):
        subflds.extend([str(n+1), keytuple[n]])
    record.add_field(Field(tag='9xx', indicators=[' ',' '], subfields=subflds))
        
        
def createWorkKey(record):
    #create the most plausible work keys of the record
    #the workKey is a list of tuples, each representing a key
    #Each key is composed of the values of the fields and subfields most likely to represent 
    #the work represented by record.
    
    # Original title?
    varTitle = record.get_fields('246')
    if len(varTitle)>0:
        iFld = varTitle[0].get_subfields('i')
        if len(iFld)>0:
            if similar(iFld[0], 'Originaltittel', method=1):
                return workKeyFromOriginalTitle(record)
    unititl = record.get_fields('130')           
    if len(unititl)>0:
        return workKeyFromUniformTitle(record)
    titl = record.get_fields('245')
    if len(titl)>0:
        return workKeyFromTitle(record)
        
def workKeyFromOriginalTitle(record):
    #1. Specifies the fields and subfields upon which to base the workKey for this record
    #2. generates the workKey based on this specification, and assigns it to field '9xx', subfields '1', '2', etc of the record
    #3. Returns the workKey as a tuple
    #Assumption: Field 246 exists and represents original title. 
    keys=[]
    for n in range(len(record.get_fields('246'))):
        if len(record.get_fields('246')[n].get_subfields('i'))>0:         #is this occurrence an original title
            keySpec=[('246',n, ['a'])]
            mainEntry=record.get_fields('100', '110', '111', '130') #returns 0 or 1 field
            if len(mainEntry)>0:
                keySpec.extend([(mainEntry[0].tag,0, ['a', 'b', 'c','d', 'e']),(mainEntry[0].tag,0, ['0'])])
            elif len(record.get_fields('245'))>0:
                keySpec.append(('245', 0, ['a', 'b']))
            key=workKey(record, keySpec)
            assignWorkKey(record, key)
            keys.append(key)
    return keys

def workKeyFromUniformTitle(record):
    #1. Specifies the fields and subfields upon which to base the workKey for this record
    #2. generates the workKey based on this specification, and assigns it to field '9xx', subfields '1', '2', etc of the record
    #3. Returns the workKey as a tuple
    #Assumption: Field 130 exists and represents uniform title
    keySpec=[('130',0, [])]
    key=workKey(record, keySpec)
    assignWorkKey(record, key)
    return [key]

def workKeyFromTitle(record):
    #1. Specifies the fields and subfields upon which to base the workKey for this record
    #2. generates the workKey based on this specification, and assigns it to field '9xx', subfields '1', '2', etc of the record
    #3. Returns the workKey as a tuple
    #Assumption: Field 245 exists and represents original title
    keySpec=[('245',0, ['a', 'b'])]
    uniform=record.get_fields('240')
    if len(uniform)>0:
        keySpec.append(('240',0, []))
    mainEntry=record.get_fields('100', '110', '111', '130') #returns 0 or 1 field
    if len(mainEntry)>0:
        keySpec.extend([(mainEntry[0].tag,0, ['a', 'b', 'c','d', 'e']),(mainEntry[0].tag,0, ['0'])])
    key=workKey(record, keySpec)
    assignWorkKey(record, key)
    return [key]
    
def similarity (str1, str2, method=0):
    #calculates the similarity between 2 strings,
    #using various methods:
    # Method 0 is exact 
    # Method 1 is difflib.SequenceMatcher 
    # Method 2 is Jaccard (Lars)
    # Method 3 is Levinstein difference (not implemented)
    similarity = 0
    if method == 0:
        if  str1 == str2: 
            similarity = 1
        else: similarity = 0
    elif method ==1:
        s=SequenceMatcher()
        s.set_seq1(str1)
        s.set_seq2(str2)
        similarity = s.ratio()
    else: similarity = 0
    return similarity
    
def similar (str1, str2, method=0, cutoff=0.9, compReq='all'):
    if isinstance(str1, list) and isinstance(str2, list):
        return similarityLists(str1, str2, method, compReq) >= cutoff
    else:
        return similarity(str1, str2, method) >= cutoff

def similarityLists(lst1, lst2, method=0, req='all'):
    #calculates similarity between lists of strings
    #generates  a list of similarity-values. Each similarity value=similarity between corresponding elements in  each list
    #len(simlist)=max(len(lst1), len(lst2)). For de siste elementene i den lengste listen blir similarity=0
    #RrReq designates the degree of completeness of the comparison between lst1 and the lst2. 
    #   'all': all items in lst1 is to be compared pairwise with the items in lst2. Resulting similarity is the 
    #          average of the pairwise similarities
    #   'allExist': all items in lst1 must be similar to some item in lst2. 
    #   'oneExists': at least one item in lst1 must be similar to some item in lst2

    simlist=[]
    if req=='all':
        for i in range(min(len(lst1), len(lst2))):
            simlist.append(similarity(lst1[i], lst2[i], method))
        for i in range(abs(len(lst1)-len(lst2))):               
            simlist.append(0)                          #penalty for unequal length of lst1 and lst2
        return numpy.average(simlist)
    if req in ['allExist', 'oneExists']:
        for e1 in lst1:
            templst=[0]
            for e2 in lst2: 
                templst.append(similarity(e1, e2, method))
            simlist.append(max(templst))            #the highest similarity to any of the elements in lst2 counts
        if req=='allExist':
               return numpy.average(simlist)
        else:
               return max(simlist)

def pairWiseSimilarity(lst1, lst2, method=0):
    #calculates similarity between lists of strings
    #generates  a list of similarity-values. Each similarity value=similarity between corresponding elements in  each list
    #len(simlist)=max(len(lst1), len(lst2)). For de siste elementene i den lengste listen blir similarity=0
    #For further calculation of the similarities, see similarityLists
    simlist=[]
    for i in range(min(len(lst1), len(lst2))):
        simlist.append(similarity(lst1[i], lst2[i], method))
    for i in range(abs(len(lst1)-len(lst2))):               
        simlist.append(0)                          #penalty for unequal length of lst1 and lst2
    return simlist
    
            


# In[ ]:




