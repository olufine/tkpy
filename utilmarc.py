#!/usr/bin/env python
# coding: utf-8

# # Utils for marc record sets 

# In[ ]:


from io import StringIO
import pymarc
from pymarc import Record, marcxml, Field, XMLWriter

#local modules
import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)
    
import marcpy2

# debugging
import pdb
import traceback


# In[4]:


def unionRecords(*recordSets, form=0):
    #returns a dict (if form=0) or list of all unique records in recordSets (unique accordin to MMSId (fld 001))
    #Assumes that each recordset contains only unique records
    total=dict()
    for recs in recordSets:
        indx=marcpy2.indexRecords(recs)
        #Add records that are not in total already
        for mms in set(indx.keys()).difference(set(total.keys())):
            total[mms]=indx[mms]
    if form==0:
        return total
    else:
        return list(total.values())

def intersectionIDs (records1, records2):
    #Calculates intersection between data sets records1 and records2
    #Returns a list shared MMS Ids (value of field 001) 
    ids1= list(map (lambda x: x.get_fields('001')[0].value(), records1))
    ids2= list(map (lambda x: x.get_fields('001')[0].value(), records2))
    return list (set(ids1).intersection(ids2))

def mergeRecordIndexes(indexes):
    #indexes is a list of dicts, Each dict has a single object (record) as value
    #returns a Dict which is a merge between the dictionaries in indexes 
    #for keys that are found in more than one index, it is assumed that their values records are equal,
    #so just choose the last of them as values
    #Typically used to merge dicts created by marcpy2.indexRecords. Does the same as unionRecords with form=0
    #collect all keys
    allkeys=[]
    for ind in indexes:
        allkeys=list(set(allkeys).union(set(list(ind))))
    #Create the dictionary
    merged=dict()
    #Initialize
    #Collect values from dictionaries
    for k in sorted(allkeys):
        for ind in indexes:
            if k in ind.keys():    #list(d) == list(d.keys())
                merged[k]=ind[k]
    return merged

def fetchRecordsFromIndex(ids, recindex):
    #Returns a list of records corresponding to the ids (mms ids)
    #recindex is a dict as created by recordIndex
    res=[]
    for ide in ids:
        if ide in recindex.keys():
            res.append(recindex[ide])
    if len(ids) > len(res):
        print('Number of records not found:', len(ids)-len(res))
    return res

def termsWdollar2(records, fieldtag, sourcecode):
    #Identifies all fields in records with tag=fieldtag and $2=sourcecode
    #Returns a list of all unique terms (subfield a values) occurring in those fields
    terms=[]
    flds=marcpy2.filterFields(records, sourcecode, [fieldtag], subfieldtags=['2'])
    for fld in flds:
        val=fld.get_subfields('a')
        if val!= []:
            terms.append(val[0])
    return (list(set(terms)), len(terms))

def duplicateFields (f1, f2, compare=['a', '2'], comparetag=True):
    #Generalisering av duplicate655
    #If compareTag=True: Returns True iff f1 and f2 have equal tag and have exactly the same values on subfields listed in compare
    #If comaperTag=False:Returns True iff f1 and f2 have xactly the same values on subfields listed in compare
    #       irrespective of field tag
    #Note: Returns True even if both f1 and f2 are empty (no a, 2 nor 0 subfields) (if tags are the same of comparetag=False)
    lik=False if (comparetag and f1.tag!=f2.tag) else True
    i=0
    while lik and i < len(compare):
        s1=sorted(list(map (lambda x: x.strip(), f1.get_subfields(compare[i]))))
        s2=sorted(list(map (lambda x: x.strip(), f2.get_subfields(compare[i]))))
        if s1==s2:
            i+=1 
        else:
            lik=False
    return lik

def fieldInRecord(record,field, compare=['a', '2']):
    #Generalisation of genreInRecord
    #Returns True iff record contains a field with same tag as field
    #and which is a duplicate (according to duplicateFields with comparetag=True)
    #of field (field is assumed to be a 655 field)
    found=False
    flds=record.get_fields(field.tag)
    i=0
    while not found and i<len(flds):
        if duplicateFields(field, flds[i], compare, comparetag=True):
            found=True
        else:
            i+=1
    return found

def multipleSubFields (records, fieldtag, subfieldtag):
    #Returns a list of records in records that have more than 1 occurrence og subfieldtag in any fieldtag
    res=[]
    for rec in records:
        flds=rec.get_fields(fieldtag)
        for fld in flds:
            if len(fld.get_subfields(subfieldtag)) >1:
                res.append(rec)
    return (list(set(res)))

def isbnNorm(record, sep='-'):
    #Returns a normalised version of the first isbn (020)
    isbn=''
    isbns=[]
    for f in record.get_fields('020'):
        isbns.extend(f.get_subfields('a'))
    if isbns!=[]:
        isbn=''.join(isbns[0].split(sep))
    return isbn

def nzMmsId(record):
    #Returns the nz MMsId of record, i.e. either MMSd (fld 001, or the last 035 with prefix (EXLNZ-47BIBSYS_NETWORK)
    ide=record.get_fields('001')[0].value()
    if ide.endswith('2201'):
        return ide
    else:
         for fld in record.get_fields('035'):
                f35=fld.get_subfields('a')[0]
                if '(EXLNZ-47BIBSYS_NETWORK)' in f35:
                    ide=f35.partition(')')[2]    #strip off the EXLNZ... prefix
    if ide.endswith('2201'):
        return ide
    else:
        #001 does not end with 2201, and no 035 field with prefix (EXLNZ-47BIBSYS_NETWORK) was found
        return None

def mmsId(record):
    return record.get_fields('001')[0].value()

def overlap(bibl1, codebibl2):
    #Returns the overlap between the dataset bibl1 and another dataset indicated by 913$a<codebibl2>
    #That is, the records in bibl1 for which 913$a<codebibl2> exist
    #Tolerate 1st character lower and uppercase
    r='('+codebibl2[0].lower() + '|' + codebibl2[0].upper() + ')' + codebibl2[1:] #Parentheses are necessary!
    if bibl1 !=[]:
        result=marcpy2.filterRecords(bibl1, r,['913'])
    else:
        result= []
    return result


# In[ ]:





# In[ ]:




