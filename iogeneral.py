#!/usr/bin/env python
# coding: utf-8

# ## XML and general I/O functions

# In[1]:


from pprint import pprint as pp
import xml
from xml import etree
from xml.etree import ElementTree
from io import StringIO
import csv
import unicodedata as ucd
# debugging
import pdb
import traceback


# In[2]:


def writeToFile(records, filename, encoding='utf-8'):
    #records is a list of xml.etree.Element instances
    #wraps records in a collection element to a ElementTree instance
    #write the ElementTree to file
    root= xml.etree.ElementTree.Element('collection')
    for rec in records:
        root.append(rec)
    e3=xml.etree.ElementTree.ElementTree(root)
    e3.write(filename, encoding)

def writelist(file, contentLst, encoding='utf-8'):
    #writes contentLst to file, each elemnet per line
     with open(file, 'w', encoding=encoding) as f:
        for elt in contentLst:
            f.write(str(elt) + '\n')
        f.close()

def writeDictToCSV(csvfile, contentDict, delim='|', encoding='utf-8'):
    #writes contentDict to csvfile,using 2 columns (key to the left, value to the right)
     with open(csvfile, 'w', encoding=encoding) as f:
        thiswriter=csv.writer(f, delimiter = delim)
        for itm in contentDict.items():
            thiswriter.writerow(itm)
        f.close()
        
def accumulateCSVfiles(csvfiles, delim='\t'):
    #reads all files in csvfiles into one list of lists of strings
    result = []
    for f in csvfiles:
        with open(f, newline='', encoding='UTF-8') as csvfl:
            thisreader=csv.reader(csvfl, delimiter = delim)
            for row in thisreader:
                result.append(row)
            csvfl.close()
    return(result)
            
def writeGroupedRowsToCSV(filename, data, delim='|'):
    #writes data to a csv file.
    #data is a list of lists of lists.  The innemost lists corresp. to a row in the file
    #data=[[[grp1row1....],[grp1row2....]], ...,[[grpXrow1....],[grpXrow2....]],... ]
    with open(filename, 'w', newline='',  encoding = 'utf-8') as f:
        thiswriter=csv.writer(f, delimiter = delim)
        for group in data:
            for rw in group:
                thiswriter.writerow(rw)
        f.close()

def writeRowsToCSV(filename, data, delim='|'):
    #writes data to a csv file.
    #data is a list of lists or tuples
    with open(filename, 'w', newline='',  encoding = 'utf-8') as f:
        thiswriter=csv.writer(f, delimiter = delim)
        for rw in data:
               thiswriter.writerow(rw)
        f.close()

def readlines(file, encoding='utf-8'):
    #reads the entire content of file, and returns its content as a list
    with open(file, 'r', encoding=encoding) as f:
        content = f.readlines()
    f.close()
    result = []
    for ln in content:
        result.append(ln[0:-1])  # remove line feed at the end of each line
    return result

def readCsvRows(csvfile, encoding='utf-8', delim=';'):
    #reads the entire content of csvfile
    #returning a list of tuples, each tuple corresponding to 1 row
    content=[]
    with open(csvfile, 'r', encoding=encoding) as f:
        thisreader=csv.reader(f, delimiter=delim)
        for row in thisreader:
            content.append(tuple(row))
        f.close
    return content
    
def writeDictAsJson(datadict, filename, indent=4, sort_keys=False):
    #writes a dict to a file
    #datadict is a dict
    with open(filename, 'w') as f:
        json.dump(datadict, f, indent=indent, sort_keys=sort_keys)
        f.close()

def writeall(fname, content, encoding='utf-8'):
    #writes content to file
    #assumes the content is formatted correctly
     with open(fname, 'w', encoding=encoding) as f:
        f.write(content)
        f.close()

def key(elt):
    return elt[0][0]    

