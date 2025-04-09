#!/usr/bin/env python3
"""
    Rydder i eksportfil fra tematres og konverterer fra rdf/xml til ttl. Sammenligner med sist publiserte versjon 
    og markerer endrede begreper med DCTERMS.modified, ev. OWL.deprecated
        
    Parameter
    ----------
    rdf-filnavn 
    ttl-filnavn for siste publiserte (i nbvok) versjon
    konfigurasjonsfil
    
    Retur
    -------
    ttl legges i ny fil (navn etter input konfigurasjonsfilnavn)
    Meldinger fra skosify til konverter.log
    

"""
import rdflib
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDF, RDFS, XSD, OWL, DCTERMS
from lxml import etree
import skosify
import re
import datetime
from datetime import datetime


def konverter(filnavn, frgfilnavn, konfignavn):
    
    konf = __import__(konfignavn)
    uribase = konf.uribase
    tematres_uribase = konf.tematres_uribase
    languages = ','.join (['"'+x+'"' for x in konf.languages])
    tabort=konf.remove_subtrees
    
    dom = etree.parse(filnavn)
    
    fiksRDF(dom, konf)
        
    with open('tmp.xml', 'w', encoding='utf-8') as utxml:
        utxml.write(etree.tostring(dom, pretty_print=True, encoding='utf-8').decode("utf-8"))
        
    skosifyconfig = skosify.config()
    skosifyconfig['enrich_mappings'] = False
    voc = skosify.skosify('tmp.xml', **skosifyconfig)
    
    #Fjern eventuelle subtrær som ikke skal publiseres (ennå)
    #voc har fortsatt tematres-urier
    for ide in tabort:
        removeTree(voc, URIRef(tematres_uribase+str(ide)))
        
    voc.serialize(destination='tmp.ttl', format='ttl')

    # Rydd opp i uri-base og dateTime i ttl-filen:
    
    
    with open ('tmp.ttl', 'r', encoding='utf-8') as ttl:
        with open ('tmp2.ttl', 'w', encoding='utf-8') as ut:
            ut.write ("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
            for lin in ttl:
                lin = lin.replace(tematres_uribase,uribase)
                if 'dct:' in lin:
                    # fiks datetime format
                    lin = re.sub("(\d+)\s(\d\d:\d\d:\d\d\")", r"\1T\2^^xsd:dateTime", lin)
                if 'dc:language' in lin:
                    lin = re.sub("(\s*dc:language\s*).*", r"\1"+languages+';', lin)
                ut.write (lin)
    
    #Les inn grafen (med oppdaterte URI-er) på nytt og rydd opp språk-tagger, dct:modified og owl:deprecated
    new_gr=Graph()
    new_gr.parse('tmp2.ttl', format='n3')
    prev_gr=Graph()
    prev_gr.parse(frgfilnavn, format='n3')
    replaceLangtags(new_gr)
    markmodified(prev_gr, new_gr)
	
    utfilnavn = konf.grafnavn if konf.grafnavn.endswith(".ttl") else konf.grafnavn+".ttl"
    print ("\n\nResultat-fil: ", utfilnavn)
    new_gr.serialize(destination=utfilnavn, format='ttl', encoding='utf-8')
    
def removeTree(graph, topEntity):
    #removes from graph the subtree starting with topEntity
    #Method: 1) Collects all nodes in subtree using SKOS.narrower
    #        2) Removes all triples in which the nodes are subject or object
    nodes=[topEntity]
    nodes.extend(traverseRelated(graph, topEntity, SKOS.narrower))
    removeConcepts(graph, nodes)

def traverseRelated(graph, entity, relation):
    #returns a list of all entities obtained when traversing relation from entity
    #until dead ends
    nodes=related (graph, entity, relation) #first level
    for node in nodes:
         nodes.extend(traverseRelated(graph, node, relation))
    return list(set(nodes))    

def removeConcepts(g, concepts):
    #removes all triples having any of the concepts in concepts as subject or object
    for c in concepts:
        g.remove((c,None,None))
        g.remove((None,None,c))

def related (graph, entity, relation):
    #returns the entities in g related to entity by relation
    related=[]
    for ent in graph.objects(entity,relation):
        related.append(ent)
    return list(set(related))
    
def entities(graph, entityType):
    #Returns a list of distinct entities of the given type in graph
    entityRefs=[]
    for ent in graph.subjects(RDF.type, entityType):
        entityRefs.append(ent)
    return list(set(entityRefs))

def subjectlist(graph):
    #Returns the list of distinct subjects
    entityRefs=[]
    for ent in graph.subjects(None, None):
        entityRefs.append(ent)
    return list(set(entityRefs))

 
def replaceLangtags(graph, tag2tag= [('nb-NB', 'nb'), ('no', 'nb')], 
                    props=[SKOS.prefLabel, SKOS.altLabel, SKOS.definition, SKOS.scopeNote, SKOS.example, SKOS.note]):
    #replaces language tags according to tag2tags tuples (replace 1st element with 2nd)
    for p in props:
        for t2t in tag2tag:
            for tr in graph.triples((None, p, None)):
                if type(tr[2])==Literal and tr[2].language==t2t[0]:    #language can be called for all Literals, also dateTime
                    graph.remove(tr)
                    graph.add((tr[0], tr[1], Literal(str(tr[2]), lang=t2t[1]))) 
                    
def markmodified (oldGraph, newGraph, dtm=datetime.now()):
    #Find all concepts that have different triples between oldGraph and newGraph
    # and mark them modified
    #dtm is a datetime object, which is to be set as a modification time
    #The graph of updates (set of triples that reside in one graph, but not in both)
    updates=oldGraph^newGraph    #updates is a Graph
    updates.remove((None, DCTERMS.created, None))
    updated=subjectlist(updates)  #Cannot use entities, as the type triples are not necessarily included there
    #Do any entities exist only in the old Graph?
    nolongerIncluded=list(set(updated).difference(set(entities(newGraph, SKOS.Concept))))
    #Some of them may have been deprecated earlier
    deprecated=[]
    for d in nolongerIncluded:
        if updates.value(subject=d, predicate=OWL.deprecated) == Literal(True):
            deprecated.append(d)
    #The rest must be deprecated now
    todeprecate=list(set(nolongerIncluded).difference(set(deprecated)))
    #Update newGraph
    for ent in updated:
        if ent in deprecated:
            copy(oldGraph, ent, newGraph)
        elif ent in todeprecate:
            deprecate(oldGraph, ent, newGraph, dtm)
        else:
            #Concepts for which (c, dct:modified, dte) are the only triples in updates, are not really updated
            if realchange(updates, ent) == True:
                newGraph.remove ((ent, DCTERMS.modified, None))
                newGraph.add((ent, DCTERMS.modified, Literal(dtm.isoformat(timespec='seconds'), datatype=XSD.dateTime)))
            else:
                #ent has only (ent, dct:modified, None) in updates
                #Then ent is not really updated, but has been marked/updated as modified through a previous publishing
                copy(oldGraph, ent, newGraph)
 

def copy (graph, concpt, newGraph):
    #Copy concpt in graph and add to newGraph
    #Remove entity from newGraph (if it exists there)
    newGraph.remove((concpt, None, None))
    newGraph+=graph.triples((concpt, None, None))

def deprecate (graph, concpt, newGraph, deprTime):
    #Copy concpt it from graph to newGraph, and add owl:deprecated=True to concpt
    #Set or update dct:modified
    copy (graph, concpt, newGraph)     
    newGraph.add((concpt, OWL.deprecated, Literal(True, datatype=XSD.boolean)))
    newGraph.remove ((concpt, DCTERMS.modified, None))
    newGraph.add((concpt, DCTERMS.modified, Literal(deprTime.isoformat(timespec='seconds'), datatype=XSD.dateTime)))

def realchange(diffgraph, concpt):
    #Return True if diffgraph contain at least one triple (concpt, p,o)
    #in which p is not dct:modified
    realch=set(diffgraph.triples((concpt, None, None))).difference(set(diffgraph.triples((concpt, DCTERMS.modified, None))))
    return realch!=set() 
                       
def fiksRDF(dom, konf):
    xml = "{http://www.w3.org/XML/1998/namespace}"
    ns_map = {"dc": "http://purl.org/dc/elements/1.1/", 
                  "dct":"http://purl.org/dc/terms/",
                 "skos":"http://www.w3.org/2004/02/skos/core#",
                 "rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#"}                 
    dc = '{' + ns_map["dc"] + '}'
    rdf = '{' + ns_map["rdf"] + '}'
    skos = '{' + ns_map["skos"] + '}'

    for scheme in dom.findall('/skos:ConceptScheme', ns_map):
        for subnode in list(scheme):
            if not subnode.attrib and not (subnode.text and subnode.text.strip()): 
                scheme.remove(subnode)

        scheme.attrib[rdf+'about'] = konf.skjema
        c = etree.Element(skos+"prefLabel")
        c.attrib[xml+"lang"] = "nb"
        c.text = konf.preflabel_nb
        scheme.append(c)
        c = etree.Element(skos+"prefLabel")
        c.attrib[xml+"lang"] = "nn"
        c.text = konf.preflabel_nn
        scheme.append(c)
        c = etree.Element(skos+"prefLabel")
        c.attrib[xml+"lang"] = "en"
        c.text = konf.preflabel_en
        scheme.append(c)

        c = etree.Element(dc+"type")
        c.text = konf.dctype
        scheme.append(c)

        c = etree.Element(dc+"description")
        c.attrib[xml+"lang"] = "nb"
        c.text = konf.description_nb
        scheme.append(c)
        c = etree.Element(dc+"description")
        c.attrib[xml+"lang"] = "nn"
        c.text = konf.description_nn
        scheme.append(c)
        c = etree.Element(dc+"description")
        c.attrib[xml+"lang"] = "en"
        c.text = konf.description_en
        scheme.append(c)

    for concept in dom.findall('/skos:Concept', ns_map):

        for schemenode in concept.findall('skos:inScheme', ns_map):
            schemenode.attrib[rdf+"resource"] = konf.skjema

        for matchnode in concept.findall('skos:exactMatch', ns_map):    
            concept2 = matchnode.find("skos:Concept", ns_map)
            if concept2 is not None:
                about = concept2.get(rdf+"about")
                if konf.tematres_uribase in about:
                    preflabelnode = concept2.find("skos:prefLabel", ns_map)
                    if preflabelnode is not None:
                        concept.append(preflabelnode)
                        concept.remove(matchnode)
                else:
                    ny = etree.Element(skos+"exactMatch")
                    ny.attrib[rdf+"resource"] = about
                    concept.remove(matchnode)
                    concept.append(ny)


        for matchnode in concept.findall('skos:closeMatch', ns_map) + concept.findall('skos:partialMatch', ns_map):    
            concept2 = matchnode.find("skos:Concept", ns_map)
            if concept2 is not None:
                about = concept2.get(rdf+"about")
                if konf.tematres_uribase in about:
                    preflabelnode = concept2.find("skos:prefLabel", ns_map)
                    if preflabelnode is not None:
                        preflabelnode.tag = skos+"altLabel"
                        concept.append(preflabelnode)
                        concept.remove(matchnode)
                else:
                    ny = etree.Element(skos+"closeMatch")
                    ny.attrib[rdf+"resource"] = about
                    concept.remove(matchnode)
                    concept.append(ny)
                    
        for matchnode in concept.findall('skos:broadMatch', ns_map):    
            concept2 = matchnode.find("skos:Concept", ns_map)
            if concept2 is not None:
                about = concept2.get(rdf+"about")
                if not konf.tematres_uribase in about:
                    ny = etree.Element(skos+"broadMatch")
                    ny.attrib[rdf+"resource"] = about
                    concept.remove(matchnode)
                    concept.append(ny)

        for matchnode in concept.findall('skos:narrowMatch', ns_map):    
            concept2 = matchnode.find("skos:Concept", ns_map)
            if concept2 is not None:
                about = concept2.get(rdf+"about")
                if not konf.tematres_uribase in about:
                    ny = etree.Element(skos+"narrowMatch")
                    ny.attrib[rdf+"resource"] = about
                    concept.remove(matchnode)
                    concept.append(ny)




#Do it!
if __name__ == "__main__":
    import sys
    import os
    sys.stderr = open('konverter.log','w', encoding='utf-8')

    try:
        rdffilnavn = sys.argv[1]
        frgfilnavn = sys.argv[2]
        konfignavn = sys.argv[3].split('.')[0]
        
        print (rdffilnavn, konfignavn)
        konverter(rdffilnavn, frgfilnavn, konfignavn)
    except IndexError:
        print ("FEIL: Mangler argumenter: rdf-fil, konfigurasjon")
    except:
        print("FEIL:", sys.exc_info()) 
    finally:
        os.remove('tmp.xml')
        os.remove('tmp.ttl')
        os.remove('tmp2.ttl')

