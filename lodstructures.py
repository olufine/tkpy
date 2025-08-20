#!/usr/bin/env python
# coding: utf-8

# # Linked data structures (ontologies, hierarchies, etc)
# 

# In[1]:


from pprint import pprint as pp
import re #regular expressions
import requests
import xml
from xml import etree
from xml.etree import ElementTree
from io import StringIO
#import pymarc
#from pymarc import Record, marcxml, Field, XMLWriter, MARCReader, MARCWriter
from collections import Counter
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
import sqlite3
import json


# In[ ]:


import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)
import iogeneral, rdfhandling, utils
from rdfhandling import inverseRelated, findClosest, findClosestInverse, label1, label2, related


# In[2]:


# import rdflib
import rdflib
from rdflib import Graph, ConjunctiveGraph
from rdflib import URIRef, BNode, Literal, Namespace
from rdflib.namespace import XSD, RDF, RDFS, SKOS, OWL, DC, FOAF
from pprint import pprint as pp
from rdflib.plugins.serializers import n3, rdfxml, turtle 

#import surf             (surf no good for Python 3.x)
from SPARQLWrapper import SPARQLWrapper, JSON, XML, CSV, RDFXML, TURTLE, JSONLD

from IPython.display import display, display_pretty, display_html, HTML
#from graphviz import Digraph
import skosify


# # Hierarchies as tables

# In[ ]:


def structuredNodes(graph, nodes, hrel, sep, sortfunc=lambda x: 0):
    #Assumption: hrel is an upward relation defining a hierarchy
    #Identifies all nodes in nodes for which hrel is None (topnodes)
    #For each topnode, create its subtree based on hrel,. Returns the hierarchy as a list of lists
    #One list per topnode, containing an ordered set of tuples representing the hierarchy inside
    #That is: Only 2 levels of lists
    #sortfunc is a function used to sort the nodes. Must take nodes as an argument.
    #Default value of sortfunc implies no sorting 
    hier=[]
    topnodes=[]   #nodes for which hrel is empty or is not in nodes
    for n in nodes:
        #over=related(graph, n, hrel)
        #if over==[] or 1 not in list(map(lambda x: 1 if x in nodes else 0, over)):
        over=findClosest(graph, n, hrel, nodes)
        if over==[]:
            topnodes.append(n)
    topnodes.sort(key=sortfunc)
    i=1
    #Create the subtree under each topnode in no
    for tn in topnodes:
        hier.append(listHierarchy(graph, tn, str(i), hrel, nodes, sep, sortfunc=sortfunc))
        i+=1
    return hier

def listHierarchy(graph, startnode, key, hrel, nodesdomain, sep, sortfunc=lambda x: 0):
    #creates a list of pairs representing the hierarchy defined by hrel, starting from startnode
    #Pairs: First element is a key indicating the second element's (a node) place in the hierarchy
    #Only nodes in nodesdomain are considered
    #Assumption: hrel points upwards (e.g. subPropertyOf)
    res=[(key, startnode)]
    i=1
    #for s in sorted(list(graph.subjects(hrel, startnode)), key=sortfunc):
    for s in sorted(findClosestInverse(graph, startnode, hrel, nodesdomain), key=sortfunc):
        if s in nodesdomain:
            k=key+sep+str(i)
            i+=1
            res.extend(listHierarchy(graph, s, k, hrel, nodesdomain, sep, sortfunc=sortfunc))
    return res


# # Ontology handling (RDFS, etc)

# In[2]:


def hasDomain(graph, prop, domain):
    #returns True if domain is the triple (prop, RDFS.domain, domain) exists
    #Does not consider superclass of domain
    if domain in related(graph, prop, RDFS.domain):
        return True
    else:
        return False
    
def topProperties(graph, dclass):
    #returns the properties of dclass which have no super properties with sclass as domain
    allprops=inverseRelated(graph, dclass, RDFS.domain) #all properties 
    tops=[]
    for p in allprops:
        supers=related(graph,p, RDFS.subPropertyOf)
        if supers==[]:
            tops.append(p)    #no super property
        elif set(list(map(lambda x: hasDomain(graph, x, dclass), supers))) == {False}:
            tops.append(p) #none of the super properties have dclass as declared domain
    return tops

def getHierarchy(graph, entity, hrelation):
    #returns a dict (of dicts) of all entities obtained when traversing hrelation from entity
    #until dead ends
    #Used to represent the hierarch as represented by hrelation
    d=dict()
    nodes=inverseRelated (graph, entity, hrelation) #first level
    for node in nodes:
         d[node]=getHierarchy(graph, node, hrelation)
    return d

def getHierarchyLabels(graph, entity, hrelation, lang='en'):
    #returns a dict (of dicts) of all entities obtained when traversing hrelation from entity
    #until dead ends
    #Used to represent the hierarch as represented by hrelation
    d=dict()
    nodes=inverseRelated (graph, entity, hrelation) #first level
    for node in nodes:
         d[label2(graph, node, lang=lang)]=getHierarchyLabels(graph, node, hrelation, lang=lang)
    return d



# In[63]:




