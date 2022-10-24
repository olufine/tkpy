#!/usr/bin/env python
# coding: utf-8

# # Functions for Marc handling - 2
# 

# In[6]:


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
import unicodedata as ucd
# debugging
import pdb
import traceback

#local modules
import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)
#import utils
#import iogeneral
#import iomarc
#import marcpy1
from marcpy1 import fieldValue


# In[7]:


def filterRecords(records, regpattern, fieldtags, subfieldtags=[]):
    #returns a sublist of records, containing the records 
    #where the value on at least one of fieldtags (and subfieldtags]) matches regpattern
    result = []
    for rec in records:
        patternFound=False
        n=0
        flds=rec.get_fields(*fieldtags)
        if len(flds) > 0:
            while (not patternFound) and (n<len(flds)):
                if subfieldtags == []:
                    valuestr=flds[n].value()  #return the whole field value if no subfieldtags are given
                else:
                    valuestr=fieldValue(flds[n], subfieldtags)
                if re.search(regpattern, valuestr) is not None:
                    patternFound=True
                n+=1
                #print(n, patternFound)
        if patternFound:
            result.append(rec)
    return result

def filterRecordsByLeader(records, regpattern, posint=(0,24)):
    #returns a sublist of records, containing the records 
    #with the given slice of leader matches regpattern
    #posint is a 2-tuple indicating the first and last position to check (starting at 0)
    result = []
    for rec in records:
        valuestr=rec.leader[posint[0]:posint[1]]
        if re.search(regpattern, valuestr) is not None:
            result.append(rec)
    return result

def filterRecordsByControlField(records, regpattern, fieldtag, posint):
    #New 3.5.2020
    #returns a sublist of records, containing the records 
    #with the given slice of leader matches regpattern
    #posint is a 2-tuple indicating the first and last position to check (starting at 0)
    result = []
    for rec in records:
        for fld in rec.get_fields(fieldtag):
            valuestr=fld.value()[posint[0]:posint[1]]
            if re.search(regpattern, valuestr) is not None:
                result.append(rec)
    return result
                          
def filterFields(records, regpattern, fieldtags, subfieldtags=[]):
    #Updated 10.10.2019
    #returns a list of field objects of records, containing the fields
    #for which the value (or value of at least one of subfieldtags])
    #matches regpattern
    result = []
    for rec in records:
        flds=rec.get_fields(*fieldtags)
        for fld in flds:
            if subfieldtags == []:
                valuestr=fld.value()  #process the whole field value if no subfieldtags are given
            else:
                valuestr=fieldValue(fld, subfieldtags)
            m=re.search(regpattern, valuestr)
            #Beware of patterns like <something>*. This will not return None, but an empty match
            if m is not None and m.start()!=m.end():
                result.append(fld)    
    return result

def fetchRecords(records, idList):
    #returns the sublist of records (pymarc records) corresponding to the ones 
    #for which the value of field 001 is included in idList 
    #if any ID in idList occurs more than once in records (that is, idList not unique), return None
    result=[]
    uniqueIDs=True
    for i in idList:
        r=filterRecords(records, i, ['001'])
        if len(r)==1:                   
            result.append(r[0])
        else: 
            if len(r)>1:
                uniqueIDs=False
    if uniqueIDs==True:
        return result
    else:
        return None
        
def fetchRecord(records, ident):
    #returns the record (pymarc record) for which ident is the value of field 001 
    #if more than one (ident is not unique) or ident is not found, return None
    r=filterRecords(records, ident, ['001'])
    if len(r)==1:                   
        result=r[0]
    else: 
        if r==[] or len(r)>1:
            result=None
    return result    

def fetchRecordSimple(records, ident):
    #returns the first record (pymarc record) for which ident is the value of field 001 
    #if  ident is not found, return None
    #Does not use filterRecords, and behaves slightly differently (as does not investigate to see if more than one)
    #Much more efficient that fetchRecord
    found=False
    k=0
    rec=None
    while found == False and k<len(records):
        idFlds=records[k].get_fields('001')
        if len(idFlds) == 1 and idFlds[0].value() == ident:
            found=True
            rec = records[k]
        else:
            k+=1
    return rec

