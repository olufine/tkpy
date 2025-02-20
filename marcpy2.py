#!/usr/bin/env python
# coding: utf-8

# # Functions for Marc handling - 2
# 

# In[5]:


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
import marcpy1
from marcpy1 import fieldValue, similar


# In[2]:


def select(records, fieldtag, values, subfields=None,  compMethod=0, cutoff=0.9, compReq='all' ):
    #returns the records in records for which the value of the fieldtag/subfields corresponds to values
    #subfieldds and values must be iterables. 
    #   If subfields is None, values are assumed to contain 1 element (i.e. only the 1st element is used)
    #compMethod represent the method by which the similarity is calculated (default = exact )
    #compReq designates the degree of completeness of the comparison between values and the subfields values. 
    #   'all': all items in values is to be compared pairwise with the items in the current fld.get_subfields(*subFields). 
    #          In effect, this means that values must be similar to fld.get_subfields(*subFields)
    #   'allExist': all items in values must be similar to some value in fld.get_subfields(*subFields). 
    #   'oneExists': at least one item in values must be similar to some value in fld.get_subfields(*subFields)
    result=[]
    for rec in records:
        selected=False
        if subfields is None:
            for fld in rec.get_fields(fieldtag): 
                if similar(values[0], fld.value(), compMethod, cutoff):
                    selected=True
        else:
            for fld in rec.get_fields(fieldtag): 
                if similar(values, fld.get_subfields(*subfields),compMethod, cutoff, compReq):
                    selected=True
        if selected: 
            result.append(rec)
    return result

def selectAssigned(records, fieldtag, subfields=None,  compReq='all'):
    #Update 11.10.2019 (introducing 'allIn1, and correcting the handling of 'all')
    #returns the records in records for the given combinations of fieldtag/subfields exist
    #   If subfields is None, records with at least 1 instance of fieldtag are included. In this case, compReq is ignored.
    #compReq designates the degree of completeness of the comparison between values and the subfields values. 
    #   'all': for a record to be selected, all fieldtag/subfields combinations must exist, but not necessarily 
    #          in the same  field occurrence 
    #                           Example: fieldtag='700', subfields=['a', 't'], 'all'. A record containing
    #                                    700$aIbsen, Henrik $tEt dukkehjem as well as a record containing the 2 fields 
    #                                    700$aIbsen Henrik
    #                                    700$tRosmersholm
    #                                    will be included in the result set
    #          NOT RELIABLE: fld.get_subfields(t1, td) returns the values of t1 and t2 in the order they occur in the record
    #                        not in the order given by the method call.
    #   'allIn1': Only returns records in which at least one occurence of fieldtag contains all subfields, like
    #                           Example: fieldtag='700', subfields=['a', 't'], 'allIn1'. A record containing
    #                                    700$aIbsen, Henrik $tEt dukkehjem will be included in the result set, but records 
    #                                    with only 700$a or 700$t separately will not
    #   'oneExists': for a record to be selected,at least one fieldtag/subfields combination must exist
    result=[]
    for rec in records:
        selected=False
        if len(rec.get_fields(fieldtag)) > 0:
            if subfields is None:
                selected=True
            elif compReq == 'all':
                foundSubfields=set()
                for fld in rec.get_fields(fieldtag): 
                    for sfld in subfields:
                        if len(fld.get_subfields(sfld)) > 0:       #sfld is present in fld
                               foundSubfields.add(sfld)
                if foundSubfields == set(subfields):            
                    selected=True                                 #all subfields found in one of the field occurrences
            elif compReq =='allin1':
                flds = rec.get_fields(fieldtag)
                k=0
                found=False
                while k<len(flds) and not found:
                    fld=flds[k]
                    found=True
                    for sfld in subfields:
                        if len(fld.get_subfields(sfld)) == 0:       #sfld is not present in fld
                               found=False
                    if not found:
                        k+=1
                    else:
                        selected=True                                 #all subfields found in one of the field occurrences
            else:                                                 #compReq='oneExists'
                for fld in rec.get_fields(fieldtag): 
                    if len(fld.get_subfields(*subfields))>0:       #one subfield in one of the fieldstag occurrenses is enough
                           selected = True
        if selected: 
            result.append(rec)
    return result

def selectMissingFields(records, fieldtags, all=True):
    #Returns a list of the records in records for which
    #    all the fields in fieldtags are missing (if all=True)
    #    at least one of the fields in fieldtags are missing (all=/= True)
    res=[]
    if all == True:
        for rec in records:
            if rec.get_fields(*fieldtags) ==[]:
                res.append(rec)
    else:
        for rec in records:
            someMissing=False
            i=0
            while i < len(fieldtags) and not someMissing:
                if rec.get_fields(fieldtags[i]) ==[]:
                    someMissing=True
                    res.append(rec)
                else:
                    i+=1
    return res

def someAssigned(records, fieldtags, subfields=[]):
    #Return the records in recoprds for which at least one of fieldtags are assigned
    res=set()
    for ft in fieldtags:
        res=res.union(selectAssigned(records, ft, subfields=subfields))
    return list(res)

def selectMissingSubfields(records, fieldtag, subfieldtags):
    #Returns a list of the records in records which contain at least one 
    #field for which all of the subfields in subfieldtags are missing.
    res=[]
    for rec in records:
        flds=rec.get_fields(fieldtag)
        subMissing=False
        i=0
        while i<len(flds) and not subMissing:
            if flds[i].get_subfields(*subfieldtags) == []:
                subMissing=True
                res.append(rec)
            else:
                i+=1
    return res

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

def recordsRepeatedField(records, fieldtag):
    #Returns the records (as a list) that contains more than one occurrence of fieldtag
    result=[]
    for rec in records:
        if len(rec.get_fields(fieldtag))>1:
            result.append(rec)
    return result

def recordsRepeatedSubfield(records, fieldtag, subfieldtag):
    #Returns the records (as a list) that contains fields with tag=fieldtag 
    # with more than one occurrence of subfiledtag
    result=[]
    for rec in records:
        for fld in rec.get_fields(fieldtag):
            if len(fld.get_subfields(subfieldtag))>1:
                result.append(rec)
    return result

def indexRecords(records):
    #Return a dict with MMsIds as keys and its record as value
    #To be used for efficient retrieval of single records
    indx=dict()
    for rec in records:
        ide=rec.get_fields('001')[0].value()
        indx[ide]=rec
    return indx

def indexRecords2(records, fieldtag, subfieldtags=None, sep='$'):
    #Return a dict with value of fieldtag+subfieldtags as key, and the list of matching records as value
    indx=dict()
    for rec in records:
        flds=rec.get_fields(fieldtag)
        for fld in flds:
            rkey=''
            if subfieldtags is None:
                rkey=fld.value()
            else:
                if fld.get_subfields(*subfieldtags) != []:
                    rkey=sep.join(fld.get_subfields(*subfieldtags))
            if rkey != '':
                if rkey in indx.keys():
                    indx[rkey].append(rec)
                else:
                    indx[rkey]=[rec]
    #remove duplicates
    for k in indx.keys():
        indx[k]=list(set(indx[k]))
    return indx

def indexRecords3(records, fieldtag, subfieldtags=None, sep='$'):
    #Like indexRecords2, but instead of list of records as value for each key
    # a list of tuples are the value. Second item in the tuple is the record matching the key, 
    #the first item is the display name (fld.value()) of the fielddisplay name (string, and the second is the 
    #corresponding value)
    indx=dict()
    for rec in records:
        flds=rec.get_fields(fieldtag)
        for fld in flds:
            rkey=''
            if subfieldtags is None:
                rkey=fld.value()
            else:
                if fld.get_subfields(*subfieldtags) != []:
                    rkey=sep.join(fld.get_subfields(*subfieldtags))
            if rkey != '':
                if rkey in indx.keys():
                    indx[rkey].append((fld.value(), rec))
                else:
                    indx[rkey]=[(fld.value(), rec)]
    #remove duplicates
    for k in indx.keys():
        indx[k]=list(set(indx[k]))
    return indx


# In[ ]:




