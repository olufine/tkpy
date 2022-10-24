#!/usr/bin/env python
# coding: utf-8

# # Functions for analysing bibliographies (MARC)

# In[2]:


from pprint import pprint as pp
import re #regular expressions
import requests
import urllib, urllib.parse     # used for percent-encoding strings
import xml
from xml import etree
from xml.etree import ElementTree
from io import StringIO
import pymarc
from pymarc import Record, marcxml, Field, XMLWriter
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
import csv
import difflib
from difflib import SequenceMatcher
import itertools
import numpy
import unicodedata as ucd
# debugging
import pdb
import traceback
#data storage
from wordcloud import WordCloud


#local modules on git tkpy
import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)
import marcpy1
from marcpy1 import valueCounter
import marcpy2
from marcpy2 import filterRecords,filterRecordsByLeader,fetchRecordSimple
import utils
from utils import sum


# In[ ]:


def overlap(bibl1, codebibl2):
    #Returns the overlap between the dataset bibl1 and another dataset indicated by 913$a<codebibl2>
    #That is, the records in bibl1 for which 913$a<codebibl2> exist
    #Tolerate 1st character lower and uppercase
    r='('+codebibl2[0].lower() + '|' + codebibl2[0].upper() + ')' + codebibl2[1:] #Parentheses are necessary!
    if bibl1 !=[]:
        result=filterRecords(bibl1, r,['913'])
    else:
        result= []
    return result

def authorGender(autrecs, biblrecs):
    #returns a list of 3 lists:
    #1. the biblrecs with female main authors
    #2. the biblrecs with male authors
    #3. the biblrecs with no gender info on main author
    #(biblrecs minus the union of the 3 above include records that have no main author
    #    or have main author, but no author ID, or the author ID is not found in autreg)
    females=[]
    males=[]
    noGenderInfo=[]
    #Look only at those with 100$0 field (has main author (person) and is authorised)
    withMainAuth=selectAssigned(biblrecs,'100', subfields=['0'])
    for rec in withMainAuth:
        #remove the prefix from $0
        autid = rec.get_fields('100')[0].get_subfields('0')[0][10:]
        aut=fetchRecordSimple(autrecs, autid)
        if aut is not None:
            gf=aut.get_fields('375')
            if gf!=[]:
                if gf[0].value()[0] in {'f', 'F'}:
                    females.append(rec)
                elif gf[0].value()[0] in {'m', 'M'}: 
                    males.append(rec)
            else:
                noGenderInfo.append(rec)
        else:
            noGenderInfo.append(rec)
    return [females, males, noGenderInfo]

def authorGender2(biblrecs, girls, boys):
    #returns a list of 3 lists:
    #1. the biblrecs with female main authors
    #2. the biblrecs with male authors
    #3. the biblrecs with no gender info on main author
    #girls and bouys are  lists of names extracted from SSB (https://data.ssb.no/api/v0/no/console)
    females=[]
    males=[]
    noGenderInfo=[]
    #Look only at those with 100$a field (has main author (person) and a name)
    withMainAuth=selectAssigned(biblrecs,'100', subfields=['a'])
    #Identify the individual first names in 100$a
    for rec in withMainAuth:
        names= forenames(rec.get_fields('100')[0].get_subfields('a')[0])
        if set(girls).intersection(set(names)) != set():
            females.append(rec)
        elif set(boys).intersection(set(names)) != set():
            males.append(rec)
        else:
            noGenderInfo.append(rec)
    return [females, males, noGenderInfo]

def forenames (namestring):
    #returns a list of forenames from a field 100a
    #on the form <forenames>, <last name>(s), e.g. 
    # Kvamme, Ole Andreas   --> returns [Ole, Andreas]
    # Downs, Brian H.  ---> returns [Brian]
    fnamestr=namestring.partition(',')[2].strip()
    fnames=list(map (lambda x: x.strip(), fnamestr.split(' ')))
    #Ignore abbreviations/initials
    res=[]
    for s in fnames:
        if len(s)>1 and s[-1]!='.':
            res.append(s)
    return res      
    

def publishedYears(records, groupSz=0):
    yrCounter=valueCounter(records, ['008'], slice=(7,11))   #sorted by keys (years)
    return pd.DataFrame(yrCounter.values(), index=yrCounter.keys())

def publishedBetween(records, fromYear=0, toYear=2040):
    #returns the number of records in records published in the given interval
    yrCounter=valueCounter(records, ['008'], slice=(7,11))   #sorted by keys (years)
    res=0
    for k in yrCounter.keys():
        if k.isdigit() and int(k)>=fromYear and int(k)<toYear:
            res+=yrCounter[k]
    return res

def textvolume (records):
    return textvolumeInfo(records)[2]

def textvolumeInfo (records):
    #calculates the approximate, total  number of pages or leaves in records
    #Filters out the subset of records with 'a' in Leader
    #Then calculates the number of pages or leaves from 300$a in the subset
    #Returns a tuple of 3 elements: 
    #(1)The number of records, (2)the number of text records, (3)the number of text pages or leaves
    #textrecs=filterRecordsByControlField(records, 'ta', '007', (0,2))
    textrecs=filterRecordsByLeader(records, 'a', posint=(6,7))
    textvol=sum(list(map (lambda x: textExtent(x), textrecs)))
    return (len(records), len(textrecs), textvol)

def textExtent(record):
    ext=0
    extentstr=''
    f300=record.get_fields('300')
    if f300 != []:
        sf300a=f300[0].get_subfields('a')
        if sf300a != []:
            extentstr=sf300a[0]
            ext=gatherTextExtent(extentstr)
    return ext

def gatherTextExtent(extentstring):
    #extentstring is the total content of 300a
    extentstr=extentstring
    ext=0
    if re.search('(\d b\. i 1)', extentstr) is not None:
        #remove this, the rest should detail the pages
        extentstr=extentstr.replace(re.search('(\d b\. i 1)', extentstr).groups()[0],'',1)
    elif re.search('(\d b\.)', extentstr) is not None:
        extentstr=extentstr.replace(re.search('(\d b\.)', extentstr).groups()[0],'',1)
    for extentcomp in extentstr.split(','):
            ext+=calcTextExtent(extentcomp)
    return ext

def calcTextExtent(extentstring):
    #Calculates the number of pages or leaves expressed by extsentring
    #extentstring is 1 statement in 300$a (which may contain several statements separated by comma)
    #Example of 300$a: 1 bl., 4,  [2] s., S. 595-1088, [2] s. This contains 5 extentstatments, 
    #to be processed separately here
    #examples: 
    # 148 s.| 150 s.|154 bl.|126 s.|'S. 95-96|Side 95-96 | S. 96-[118]|S. [103]-130| S. [109]-[121]
    # V|[6] | 220 s.|
    ext=0
    #1. Detect number of units like 15 s. (or S.) or 15 sider (or Sider) or 15 bl. or Bl. or blad or Blad.
    if re.search('\[?(\d+)\]?\s*((s|S)\.|(s|S)ider|(b|B)l\.|(b|B)lad)', extentstring) is not None:
        #retrieve the first matching pagenumber
        pagenum=re.search('(\d+)', extentstring).groups()[0]
        if pagenum.isnumeric() == True:
            ext+=int(pagenum)
    #2 Detect spans,  like 'S. 67 | S. 95-96|Side 95-96 | S. 96-[118]|S. [103]-130| S. [109]-[121]
    elif re.search('((s|S)\.|(s|S)ide)\s*\[?(\d+)\]?\s*-\s*\[?(\d+)', extentstring) is not None:
        pagespan=re.search('(\d+)[^\d]*(\d+)', extentstring).groups()
        #print(pagespan)
        if pagespan[0].isnumeric() == True and pagespan[1].isnumeric() == True:
            ext+=int(pagespan[1])-int(pagespan[0])
    #3 Detect span without unit in front (occurs in cases when 300a includes e.g. 's. [1]-284, 285-467',)
    elif re.search('(\d+)\]?\s*-\s*\[?(\d+)', extentstring) is not None:
        pagespan=re.search('(\d+)[^\d]*(\d+)', extentstring).groups()
        #print(pagespan)
        if pagespan[0].isnumeric() == True and pagespan[1].isnumeric() == True:
            ext+=int(pagespan[1])-int(pagespan[0])
    #3 Detect single pages, like S. 67
    elif re.search('((s|S)\.|(s|S)ide)\s*\[?(\d+)', extentstring) is not None:
        ext+=1
    #4 Detect pagenum without unit, like in 134
    elif re.search('(\d+)', extentstring) is not None:
        #Assume this is a numer of pages or leaves (occurs in cases like  300a='134, 56 s.'')
        pagenum=re.search('(\d+)', extentstring).groups()[0]
        if pagenum.isnumeric() == True:
            ext+=int(pagenum) 
    return ext        
        
def translations(records):
    #returns the records in records that appear to be translations
    return list(set(filterRecords(records, '(O|originaltit)', ['246'], ['i'])).union
                (set(selectAssigned(records, '041', ['h'])), set(selectAssigned(records,'765'))))

#Degree of unauthorised responsibles

def unauthorisedAgentsInfo(records, fieldtags, autrefSubfield):
    #Calculates the proportion (in %) of records having a field with tag in fieldtags 
    #    that do not have the subfield autrefSubfield
    #returns a tuple (number of records with unauth fieldtags (any), number of records with fieldtags (any), ratio)
    unauthLst=[]
    withFldLst=[]
    for fld in fieldtags:
        withFld=selectAssigned(records,fld)
        unauth=list(set(withFld).difference(set(selectAssigned(records, fld, autrefSubfield))))
        withFldLst.extend(withFld)
        unauthLst.extend(unauth)
    return ((len(set(unauthLst)), len(set(withFldLst)), round(100*len(set(unauthLst))/len(set(withFldLst)))))    

def unauthorisedAgents(records, fieldtags, autrefSubfield):
    #returns the list of records having at least a field with tag in fieldtags 
    #    that do not have the subfield autrefSubfield
    unauthLst=[]
    withFldLst=[]
    for fld in fieldtags:
        withFld=selectAssigned(records,fld)
        unauth=list(set(withFld).difference(set(selectAssigned(records, fld, autrefSubfield))))
        withFldLst.extend(withFld)
        unauthLst.extend(unauth)
    return list(set(unauthLst))

