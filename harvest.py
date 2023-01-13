#!/usr/bin/env python
# coding: utf-8

# # Høsting av Marc-poster fra Alma
# 

# In[14]:


import requests
import xml
from xml import etree
from xml.etree import ElementTree
from io import StringIO
#import pymarc
#from pymarc import Record, marcxml, Field, XMLWriter, MARCReader, MARCWriter


# # Harvesting records from Alma using OAI-PMH

# In[15]:


def harvestMarcViaOAI(sett='solstad',
                      baseurl='https://bibsys.alma.exlibrisgroup.com/view/oai/47BIBSYS_NETWORK/request', 
                      prefx='marc21',
                      oains= 'http://www.openarchives.org/OAI/2.0/',
                      marcns='http://www.loc.gov/MARC21/slim',
                      resumption=True):
    #harvests OAI records from baseURL, assuming  a certein XML structure of response
    #returns a list of all  Marc records in the given set
    #namespacs should have been handled as parameters.....
    ns={'oai' : oains, 'm21' : marcns}
    payload = {'metadataPrefix': prefx, 'set': sett, 'verb':'ListRecords'}
    with requests.Session() as s:
        r=s.get(baseurl, params=payload)
        #parse XML
        root=xml.etree.ElementTree.fromstring(r.text)
        #extract all marc records
        reclist=root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns)
        if resumption:
            restoken=root.find("./oai:ListRecords/oai:resumptionToken", ns)
            while restoken is not None:
                payload= {'verb':'ListRecords', 'resumptionToken': restoken.text}
                r=s.get(baseurl, params=payload)
                root=xml.etree.ElementTree.fromstring(r.text)
                reclist.extend(root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns))
                restoken=root.find("./oai:ListRecords/oai:resumptionToken", ns)
        return reclist

def harvestMarcViaOAIIncremental(sett='solstad',
                      baseurl='https://bibsys.alma.exlibrisgroup.com/view/oai/47BIBSYS_NETWORK/request', 
                      prefx='marc21',
                      oains= 'http://www.openarchives.org/OAI/2.0/',
                      marcns='http://www.loc.gov/MARC21/slim',
                      batch=200000,
                      filename='nbbestand',           
                      resumption=True):
    #harvests OAI records from baseURL, assuming  a certein XML structure of response
    #namespacs should have been handled as parameters.....
    #stores away <batch> records at a time in files <filename>_<num>.xml. Applicable ony if resumption==True
    ns={'oai' : oains, 'm21' : marcns}
    payload = {'metadataPrefix': prefx, 'set': sett, 'verb':'ListRecords'}
    with requests.Session() as s:
        r=s.get(baseurl, params=payload)     #selve høstingen
        if r.status_code == 200:
            #parse XML
            root=xml.etree.ElementTree.fromstring(r.text)
            #extract all marc records
            reclist=root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns)
            batchnum=1
            if resumption:
                restoken=root.find("./oai:ListRecords/oai:resumptionToken", ns)
                while restoken is not None:
                    payload= {'verb':'ListRecords', 'resumptionToken': restoken.text}
                    r=s.get(baseurl, params=payload)
                    if r.status_code == 200:
                        root=xml.etree.ElementTree.fromstring(r.text)
                        if len(reclist) < batch:
                            reclist.extend(root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns))
                        else:
                            writeToFile(reclist, filename+'_'+str(batchnum)+'.xml')
                            reclist=root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns)
                            batchnum+=1
                        restoken=root.find("./oai:ListRecords/oai:resumptionToken", ns)
                        
                    else:
                        #something wrong: Return status_code, restoken and what has already been harvested (reclist)
                        writeToFile(reclist, filename+'_'+str(batchnum)+'.xml')
                        return (r.status_code, restoken)
                #No more resumptions, write the remaining reclist to file
                writeToFile(reclist, filename+'_'+str(batchnum)+'.xml')

            else:
                #no resumption. Disregard batch, write the whole reclist to file
                writeToFile(reclist, filename +'.xml')     


def harvestMarcViaOAIIncremental2(sett='solstad',
                      baseurl='https://bibsys.alma.exlibrisgroup.com/view/oai/47BIBSYS_NETWORK/request', 
                      prefx='marc21',
                      oains= 'http://www.openarchives.org/OAI/2.0/',
                      marcns='http://www.loc.gov/MARC21/slim',
                      batch=200000,
                      filename='nbbestand',           
                      resumption=True ,
                      fromBatch=1):
    #Like harvestMarcViaOAIIncremental, but uses ListIdentifiers for harvesting as quickly as possible 
    #  until writing to file should begin. This is to handle possible interrupts in the harvesting process
    #  without having to repeat the whole process
    #harvests OAI records from baseURL, assuming  a certein XML structure of response
    #returns a list of all  Marc records in the given set
    #namespacs should have been handled as parameters.....
    #stores away <batch> records at a time in files <filename>_<num>.xml. Applicable only if resumption==True
    #fromBatch indicates at which point/batch the writing on file begins: Can be useful if interrupted
    ns={'oai' : oains, 'm21' : marcns}
    verb='ListIdentifiers' if fromBatch >1  else 'ListRecords'
    payload = {'metadataPrefix': prefx, 'set': sett, 'verb':verb}
    with requests.Session() as s:
        r=s.get(baseurl, params=payload)     #selve høstingen
        if r.status_code == 200:
            #parse XML
            root=xml.etree.ElementTree.fromstring(r.text)
            #extract all marc records
            if fromBatch <= 1:           #fetch records only from fromBatch onwards
                reclist=root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns)
            else:
                reclist=[]
            batchnum=1
            verb='ListIdentifiers' if batchnum < fromBatch else 'ListRecords'
            if resumption:
                restoken=root.find("./oai:" + verb + "/oai:resumptionToken", ns)
                while restoken is not None:
                    verb='ListIdentifiers' if batchnum < fromBatch else 'ListRecords'
                    payload= {'verb': verb, 'resumptionToken': restoken.text}
                    r=s.get(baseurl, params=payload)
                    if r.status_code == 200:
                        root=xml.etree.ElementTree.fromstring(r.text)
                        if len(reclist) < batch and batchnum >= fromBatch:
                            reclist.extend(root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns))
                        else:
                            if batchnum >= fromBatch:
                                writeToFile(reclist, filename+'_'+str(batchnum)+'.xml')  #w
                                reclist=root.findall("./oai:ListRecords/oai:record/oai:metadata/m21:record", ns)
                            batchnum+=1
                        restoken=root.find("./oai:" + verb + "/oai:resumptionToken", ns)
                    else:
                        #something wrong: Return status_code, restoken and what has already been harvested (reclist)
                        writeToFile(reclist, filename+'_'+str(batchnum)+'.xml')
                        return (r.status_code, restoken)
                #No more resumptions, write the remaining reclist to file
                if batchnum >= fromBatch:
                    writeToFile(reclist, filename+'_'+str(batchnum)+'.xml')
            else:
                #no resumption. Disregard batch, write the whole reclist to file
                writeToFile(reclist, filename +'.xml')  


# ## I/O functions

# In[16]:


def writeToFile(records, filename, encoding='utf-8'):
    #records is a list of xml.etree.Element instances
    #wraps records in a collection element to a ElementTree instance
    #write the ElementTree to file
    root= xml.etree.ElementTree.Element('collection')
    for rec in records:
        root.append(rec)
    e3=xml.etree.ElementTree.ElementTree(root)
    e3.write(filename, encoding)
    

