#!/usr/bin/env python
# coding: utf-8

# # RDF handling

# In[1]:


import re #regular expressions
import requests
import xml
from xml import etree
from xml.etree import ElementTree
from io import StringIO
import unicodedata as ucd
# debugging
import pdb


# In[2]:


#Importer lokale moduler
import os
import sys
repopath=os.path.abspath('../Gitrepos/tkpy')
if repopath not in sys.path:
    sys.path.append(repopath)
import konverter_v7, iogeneral, utils


# In[1]:


# import rdflib
import rdflib
from rdflib import Graph, ConjunctiveGraph
from rdflib import URIRef, BNode, Literal, Namespace
from rdflib.namespace import XSD, RDF, RDFS, SKOS, OWL, DC, DCTERMS, FOAF
from pprint import pprint as pp
from rdflib.plugins.serializers import n3, rdfxml, turtle 

#import surf             (surf no good for Python 3.x)
from IPython.display import display, display_pretty, display_html, HTML
#from graphviz import Digraph
from skosify import skosify
import json


# ### Functions related to creating the graphs from SPARQL query

# In[4]:


def createTriple(gr, s, o, valueDict, propMap):
    #adds a new triple to the graph gr
    #s is the subject of thhe triple (URI), 
    #o is the property (string, variable from SPARQL query, e.g. 'prefTitle')
    #valueDict is the dict as returned from SPARQL query with return format JSON. 
    #     Ex: for property 'qual' valueDict may be:
    #         {'datatype': 'http://www.w3.org/2001/XMLSchema#string',
    #          'type': 'literal',
    #          'value': 'kat3'}
    #propMap is a dict mapping the string o to a URI (representing the property)
    #Note: Any Literal may have either a lang or a datatype (not both)
    prop= propMap[o] if o in propMap.keys() else None
    if prop is not None:
        if 'datatype' in valueDict.keys():
            #literals with datatypes (e.g. dates)
            gr.add((s, prop, Literal(valueDict['value'], datatype=valueDict['datatype'])))
        else:                
            if 'xml:lang' in valueDict.keys():
                #strings with language tags
                gr.add((s, prop, Literal(valueDict['value'], lang=valueDict['xml:lang'])))
            else:
                if valueDict['type'] == 'uri':
                    gr.add((s, prop, URIRef(valueDict['value']))) 


def countTriples(gr, subj=None, pred=None, obj=None):
    c=1
    for tr in gr.triples((subj,pred, obj)):
        c+=1
    return c

def getDistinctSubjects(gr, pred=None, obj=None):
    #fetches all different subjects as a list
    s=[]
    for recId in gr.subjects(predicate=pred, object=obj):
        s.append(recId)
    return list(set(s))

def getDistinctObjects(gr, subj=None, pred=None):
    #fetches all different subjects as a list
    o=[]
    for recId in gr.objects(subject=subj, predicate=pred):
        o.append(recId)
    return list(set(o))

def getDistinctPredicates(gr, subj=None, obj=None):
    #fetches all different predicates between subj and obj as a list
    p=[]
    for recId in gr.predicates(subject=subj, object=obj):
        p.append(recId)
    return list(set(p))

def getWorksByCreator(gr, autURI):
    return getDistinctSubjects(gr, pred=rdawo.P10065, obj=autURI)

def creatorGraph(gr, autURI):
    #generates a new graph with the works by autURI. Includes all information about the works
    autGraph= Graph()
    bindWRNamespaces(autGraph)
    wURIs=getWorksByCreator(gr, autURI)
    for w in wURIs:
        for tr in gr.triples((w, None, None)):
            autGraph.add(tr)
    return autGraph

def getBiblByCreator(gr, autURI):
    #return a list containing the IDs of all  bibliograpgic records attached to the works of autURI
    bibls=[]
    wURIs=getWorksByCreator(gr, autURI)
    for w in wURIs:
        bibls.extend(getDistinctObjects(gr, subj=w, pred=rdau.P60313))
    return list(set(bibls))    
    


# # Graph functions

# In[5]:


def contextGraph(cGraph, context):
    #Return a Graph object containing the triples with context=context
    #cGraph is a ConjunctiveGraph
    g=Graph()
    for tr in cGraph.triples((None, None, None), context=context):
        g.add(tr)
    return g
    
def term(URIstr):
    #returns the last part of the URI (after the last '/' or '#'
    if '#' in URIstr:
        result = URIstr.rpartition('#')
    else:
        result=URIstr.rpartition('/')
    return result[2]

def entityTypes(graph, entity, uri=False):
    #entity must be an URIRef
    #returns a list of all types of entity
    #if URI=True, the types' URIRef is returned, otherwise the type label
    tps=graph.objects(entity, RDF.type)
    if uri==False:
        return list (map (lambda x: term(str(x)), list(set(tps))))
    else:
        return list (set(tps))

def propertyTypes (graph, entity, uri=False):
    #entity must be an URIRef
    #returns a list of all property types used for entity
    #if URI=True, the types' URIRef is returned, otherwise the type label
    prp=graph.predicates(entity, None)
    if uri==False:
        return list(map(lambda x: term(str(x)), list(set(prp))))
    else:
        return list(set(prp))
    
def propertyTypesForEntityType(graph, entityType, uri=False):
    #entityType must be an URIRef
    #returns a list of all property types used for all instances of entityType
    #if URI=True, the types' URIRef is returned, otherwise the type label
    propList=[]
    for ent in graph.subjects(RDF.type, entityType):
        propList.extend(propertyTypes(graph, ent, uri=uri)) 
    if uri==False:
        return list(map(lambda x: term(str(x)), list(set(propList))))
    else:
        return list(set(propList))
    
def alltypes(graph, uri=False):
    #returns a list of all distinct types in the graph
    return entityTypes(graph, None, uri=uri)

def allpropertyTypes(graph, uri=False):
    #returns a list of all distinct properties used in the graph
    return propertyTypes(graph, None, uri=uri)

def entities(graph, entityType):
    #Returns a list of distinct entities of the given type in graph
    entityRefs=[]
    for ent in graph.subjects(RDF.type, entityType):
        entityRefs.append(ent)
    return list(set(entityRefs))

## Get entities related to a given entity by any relation
def allrelated (graph, entity):
    #returns the entities in g related to entity
    related=[]
    for ent in graph.objects(entity,None):
        related.append(ent)
    return list(set(related))

## Get entities related to a given entity
def related (graph, entity, relation):
    #returns the entities in g related to entity by relation
    related=[]
    for ent in graph.objects(entity,relation):
        related.append(ent)
    return list(set(related))

def related2entityType (graph, entity, entityType):
    #returns the entities of type entityType in g related to entity
    rel=[]
    for r in allrelated(graph, entity):
        if entityType in graph.objects(r,RDF.type):
            rel.append(r)
    return list(set(rel))

def relatedByRelation(graph, relation):
    #returns a list of entity tuples relaed by relation)
    tbl=[]
    for tr in graph.triples((None, relation, None)):
        tbl.append((tr[0], tr[2]))
    return tbl

def relation(graph, entity1, entity2):
    #returns the relations connecting the 2 entities
    rel=[]
    for r in graph.predicates(entity1, entity2):
        rel.append(r)
    return list(set(rel))

def typeOf(graph, entity):
    #if the type string is desired, use entityTypes
    return list(graph.objects(entity, RDF.type))

def inverseRelated (graph, entity, relation):
    #returns the entities in g related to entity by relation
    related=[]
    for ent in graph.subjects(relation, entity):
        related.append(ent)
    return list(set(related))

## Get entities directly related to a given entity (use when you know the subject of a triple)
def relatedInverse (graph, entity, relation):
    #returns the entities in g for which entity is related by relation
    #would give the same result as related(graph, entity, InverseOf(relation))
    related=[]
    for ent in graph.subjects(relation, entity):
        related.append(ent)
    return list(set(related))

def traverseRelated(graph, entity, relation):
    #returns a list of all entities obtained when traversing relation from entity
    #until dead ends
    #Used to collect all noed in a subtree headed by entity
    nodes=related (graph, entity, relation) #first level
    for node in nodes:
         nodes.extend(traverseRelated(graph, node, relation))
    return list(set(nodes))

## Get entities which a given entity is related to  AND included in entDomain 
def findClosest(graph, entity, relation, entDomain):
    #returns the entities in g related to entity by relation (directly or indirectly) AND included in entDoamin
    #Similar to traverseRelated, but only return nodes that are in entDomain
    closest=[]
    for ent in related(graph, entity, relation):
        if ent in entDomain:
            closest.append(ent)
        else:
            closest.extend(findClosest(graph, ent, relation, entDomain))
    return list(set(closest))

## Get entities which a given entity is related to  AND included in entDomain 
def findClosestInverse(graph, entity, relation, entDomain):
    #returns the entities in g for which entity is related by relation (directly or indirectly)AND included in entDoamin
    #Similar to traverseRelated, but only return nodes that are in entDomain
    closest=[]
    for ent in relatedInverse(graph, entity, relation):
        if ent in entDomain:
            closest.append(ent)
        else:
            closest.extend(findClosestInverse(graph, ent, relation, entDomain))
    return list(set(closest))

def entitiesWname(graph, name, nameprop=RDFS.label, lang='no'):
    #Returns a list of distinct entities with name=name
    entityRefs=[]
    for ent in graph.subjects(nameprop, Literal(name, lang=lang)):
        entityRefs.append(ent)
    return list(set(entityRefs))

## Get entities directly related to entities of a given type
def related2typesByRelation (graph, entitytype, relation):
    #returns the entities in g related to entity by relation
    rel=[]
    for ent in entities(graph, entitytype):
        rel.extend(related(graph, ent, relation))
    return list(set(rel))

##Get entities with a certain value on a property
def withValue(graph, relation, val):
    wValue=[]
    for ent in graph.subjects(relation, val):
        wValue.append(ent)
    return list(set(wValue))

##Get entities of a given type which have some value on a property
def withSomeValue(graph, entType, relation):
    wValue=[]
    for ent in entities(graph, entType):
        if related(graph, ent, relation)!=[]:
            wValue.append(ent)
    return list(set(wValue))

 


# # BIBFRAME-related

# In[ ]:


def relatedInfo(graph, entities):
    #Extracts information about related entities to each entity in entities
    #returns a list of tuples
    tbl=[('Opus', 'Title', 'Related entity', 'Relation')]
    for ent in entities:
        for r in allrelated(graph, ent):
            tbl.append((ent, bestTitleLiteral(graph, ent), r, relation(graph, ent, r)[0]))
    return tbl

def contributionInfo(graph, entity):
    #Extracts information about contributors of entity (which is typically an Opus, Expression or Instance)
    tbl=[('Contribution','Agent','Name', 'AgentType', 'Role')]
    contributions=related(graph, entity , URIRef('http://id.loc.gov/ontologies/bibframe/contribution'))
    for contr in contributions:
        agent=related(graph, contr , URIRef('http://id.loc.gov/ontologies/bibframe/agent'))
        if agent!=[]:
            name=related(graph, agent[0] , RDFS.label)
            tp=related(graph, agent[0], RDF.type)
            role=related(graph, contr, URIRef('http://id.loc.gov/ontologies/bibframe/role'))
            tbl.append((contr,agent[0],name, tp, role))
    return tbl    
   
    

def languageInfo(graph, entity):
    #Returns a list of tuples containing the properties (value, label, code, part)
    #of each language entity connected to entity
    #entity is most often an expression (svde:Work) or bf:Work
    langs=[]
    uniqlangs=list(set(list(graph.objects(entity, URIRef('http://id.loc.gov/ontologies/bibframe/language')))))
    for ul in uniqlangs:
        langinfo=[]
        vals=list(graph.objects(ul,URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#value')))
        lbls=list(graph.objects(ul,URIRef('http://www.w3.org/2000/01/rdf-schema#label')))
        codes=list(graph.objects(ul,URIRef('http://id.loc.gov/ontologies/bibframe/code')))
        parts=list(graph.objects(ul,URIRef('http://id.loc.gov/ontologies/bibframe/part')))
        if vals != []:
            langinfo.append(('value: ', vals))
        if lbls!= []:
            langinfo.append(('label: ', lbls ))
        if codes!= []:
            langinfo.append(('code:  ', codes ))
        if parts!= []:
            langinfo.append(('part:  ', parts ))
        langs.append(langinfo)    
    return langs    


# # Brukt i nbvok

# In[6]:


#Fjern begrepene Film og TV-programmer, samt alle subtrær
#Forutsetning: Vokabularet har vært prosessert av konverter.py og dermed skosify
#slik at de hierarkiske relasjonene er inferert (alle hiererakiske relasjoner 
#eksisterer både som narrower og broader.)

def removeTree(graph, topEntity):
    #removes from graph the subtree starting with topEntity
    #Method: 1) Collects all nodes in subtree using SKOS.narrower
    #        2) Removes all triples in which the nodes are subject or object
    nodes=[topEntity]
    nodes.extend(traverseRelated(graph, topEntity, SKOS.narrower))
    removeConcepts(graph, nodes)
    return graph

def traverseRelated(graph, entity, relation):
    #returns a list of all entities obtained when traversing relation from entity
    #until dead ends
    #Used to collect all noed in a subtree headed by entity
    nodes=related (graph, entity, relation) #first level
    for node in nodes:
         nodes.extend(traverseRelated(graph, node, relation))
    return list(set(nodes))

def removeConceptsWithIDs(g, uribase, ids):
    #removes all triples involving the concepts represented by the list ids
    for ide in ids:
        c=URIRef(uribase+str(ide))
        g.remove((c,None,None))
        g.remove((None,None,c))

def removeConcepts(g, concepts):
    #removes all triples involving the concepts represented by the list ids
    for c in concepts:
        g.remove((c,None,None))
        g.remove((None,None,c))


# # Labler

# In[1]:


def idNum(entity):
    #returnerer den numeriske ID-en til entity (etter ?tema=)
    #Spesifikk for TemaTres
    uri=str(entity)
    return str.partition(uri, '=')[2]

# idNum(URIRef('http://tematres.nb.no/vocab/?tema=213'))  = '213'

def prefLabel(graph, entity, lang):
    #assumes only one prefLabel per lang
    #returns the prefLabel of entity in the lang language, or None
    pref=None
    for pr in graph.objects(entity, SKOS.prefLabel):
        if pr.language == lang:
            pref=pr
    return pref

def altLabel(graph, entity, lang):
    #returns the last altLabel of entity in the lang language, 
    #or None if no altLabel in lang is there
    alt=None
    for al in graph.objects(entity, SKOS.altLabel):
        if al.language == lang:
            alt=al
    return alt

def label1(graph, entity, lang):
    #returns the last RDFS.label of entity in the lang language, 
    #or None if no label in lang is there
    labl=None
    for lbl in graph.objects(entity, RDFS.label):
        if lbl.language == lang:
            labl=lbl
    return labl

def label2(graph, entity, lang='en'):
    #returns the first RDFS.label of entity in the lang language, 
    #or None if no label in lang is there
    found=False
    i=0
    lbl=None
    labels=related(graph,entity, RDFS.label)   #list of literals
    while found==False and i<len(labels):
        if labels[i].language == lang:
            found=True
            lbl=str(labels[i])
        else:
            i+=1
    return lbl        

        
    


# In[ ]:


def exactMatches(graph, lang):
    #return a list of concepts which are exact matches to some other concept
    #Here: members of some target vocabulary in language lang
    matchedPairs=relatedByRelation(graph, SKOS.exactMatch)    #a list of tuples
    #Only return those from English vocab (LCGFT subset)
    res=[]
    for m in list(map(lambda x: x[1], matchedPairs)):
        if prefLabel(graph, m, lang) is not None:
            res.append(m)
    return res

