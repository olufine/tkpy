#!/usr/bin/env python3
"""
    Rydder i eksportfil fra tematres og konverterer fra rdf/xml til ttl
        
    Parameter
    ----------
    rdf-filnavn 
    konfigurasjonsfil
    
    Retur
    -------
    ttl legges i ny fil (navn etter input filnavn)
    Meldinger fra skosify til konverter.log
    

"""
import rdflib
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
from lxml import etree
import skosify
import re


def konverter(filnavn, konfignavn):
    
    konf = __import__(konfignavn)
    print(konf)
    uribase = konf.uribase
    tematres_uribase = konf.tematres_uribase
    languages = ','.join (['"'+x+'"' for x in konf.languages])
    tabort=konf.remove_subtrees
    print(tabort)
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
    
    utfilnavn = konf.grafnavn if konf.grafnavn.endswith(".ttl") else konf.grafnavn+".ttl"
    
    print ("\n\nResultat-fil: ", utfilnavn)
    
    with open ('tmp.ttl', 'r', encoding='utf-8') as ttl:
        with open (utfilnavn, 'w', encoding='utf-8') as ut:
            ut.write ("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
            for lin in ttl:
                lin = lin.replace(tematres_uribase,uribase)
                if 'dct:' in lin:
                    # fiks datetime format
                    lin = re.sub("(\d+)\s(\d\d:\d\d:\d\d\")", r"\1T\2^^xsd:dateTime", lin)
                if 'dc:language' in lin:
                    lin = re.sub("(\s*dc:language\s*).*", r"\1"+languages+';', lin)
                ut.write (lin)
    
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
        konfignavn = sys.argv[2].split('.')[0]
        print (rdffilnavn, konfignavn)
        konverter(rdffilnavn, konfignavn)
    except IndexError:
        print ("FEIL: Mangler argumenter: rdf-fil, konfigurasjon")
    except:
        print("FEIL:", sys.exc_info()) 
    finally:
        os.remove('tmp.xml')
        os.remove('tmp.ttl')

