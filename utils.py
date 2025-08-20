#!/usr/bin/env python
# coding: utf-8

# # Utilities and string functions

# In[1]:


def trim(strng):
    #converts strn to a string without newlines and without extra spaces
    strlst=strng.splitlines()     #remove \n
    result=''
    for s in strlst:
        result = result + ' ' + s.strip()
    return result.strip()

def oneLineStr(s):
    #returns a one line version of s. I.e. without line separators, and without leading or trailing spaces on
    #    each line of s.
    return ''.join(list(map(lambda x: x.strip() + ' ', s.splitlines()))).strip()

def curePattern(pattern, specialchars):
    #inserts escape signs in front of reserved characters in regular pattersn
    pt=pattern
    for ch in specialchars:
        pt=pt.replace(ch, '\\' +ch)  #må ha 
    return pt

def reverseDict (d):
    #returns a new dict where the keys are the values of d, and the values lists of the keys of d
    #assumes that the values of d are strings or numbers (unmutable)
    r=dict()
    for k1 in d.keys():
        if type(d[k1]) in [str, int, float] and d[k1] not in r.keys():
            r[d[k1]] = [k1]
            for k2 in d.keys():
                if d[k1]==d[k2] and k2 not in r[d[k1]]:
                    r[d[k1]].append(k2)
    return r

def copyDict(dictionary):
    #returns a new Dict which is a copy of the argument dict
    cpy=dict()
    for k in dictionary.keys():
        cpy[k]=dictionary[k]
    return cpy

def mergeDicts(dictionaries, nullVal=0):
    #returns a Dict which is a merge between the dictionaries in dictionaries 
    #the values of the merged dict is a list containing  the values of  the dictionaries in 
    #dictionaries separately. Becomes a matrix
    #nullVal is the empty value
    #collect all keys
    allkeys=[]
    for d in dictionaries:
        allkeys=list(set(allkeys).union(set(list(d))))
    #Create the dictionary
    merged=dict()
    allkeys.sort()
    #Initialize
    for k in allkeys:
        merged[k]=[]
    #Collect values from dictionaries
    for k in sorted(allkeys):
        for d in dictionaries:
            if k in list(d):
                merged[k].append(d[k])
            else:
                merged[k].append(nullVal)
    return merged

def reduceNumDict(dictionary, threshold, aggrKey='other'):
    #Assumes dict has numeric values, e.g. {'nor':43, 'dan':5, etc}
    #All values less than threshold is summed up and assigned to a key aggrKey
    #Returns a new dict with all values under thresjhold are assigned to aggrKey
    res=dict()
    aggrval=0
    for k in dictionary.keys():
        if dictionary[k]<threshold:
            aggrval+=dictionary[k]
        else:
            res[k]=dictionary[k]
    res[aggrKey]=aggrval
    return res

def flatten(l):
    #returns a list of all the elements of all the lists in l. (Flattened 1 level)
    result=[]
    for elt in l:
        if type(elt)==list:
            result.extend(elt)
        else:
            result.append(elt)
    return result

def compress(seq, toRemove):
    #Returns a cpopy of seq (list or tuple) without any of the elements in toRemove
    result = []
    for elt in seq:
        if elt not in toRemove:
            result.append(elt)
    if type(seq) == tuple:
        return tuple(result)
    else:
        return result

def removePrefixes(l):
    #returns a new list with all the elements in l which are not prefixes or equal another element
    #only 1 level is handled (no nesting)
    #meant to be used for lists of strings.
    #non-strings elements are converted to strings
    deleted=[]
    for e1 in l:
        for e2 in l:
            if e1 not in deleted and str(e2).startswith(str(e1)) and len(str(e1))< len(str(e2)):
                deleted.append(e1)
    return list(set(l).difference(set(deleted)))

def iscapitalized(strng):
    #Returns True iff strng starts with an uppecase letter and the rest (of the cased letters) are lowecase
    cap=False
    if strng!='':
        if strng[0].isupper():
            if len(strng) > 1:
                if strng[1:].islower() or strng.endswith('.'):
                    cap=True
            else:
                cap=True
    return cap

def transpose(lstlst):
    #lstlst is a list of sequences.
    #returns a list of lists, in which the internal lists are transpositions of input
    #lstlst=[[1,2,3], [4,5,6], [7,8,9,10]]
    #returns[[1,4,7], [2,5,8], [3,6,9]]
    min_l=min(list(map(lambda x: len(x), lstlst)))
    result=[]
    for i in range(0,min_l):
        comp=[]
        for seq in lstlst:
            comp.append(seq[i])
        result.append(comp)    
    return result    

def modifyString(origstr, newpart, start, fillchar=' '):
    #Returns a new string based on origstr, such that newpart starts at start in the result
    if start < len(origstr)-len(newpart):
        #newpart is to be inserted in the middle
        res=origstr[0:start]+newpart+origstr[start+len(newpart):]
    elif start < len(origstr):
        #newpart replaces the end, and possibly extends the string
        res=origstr[0:start]+newpart
    else:
        #start is larger that length of origstr. Fill up with fillchar until position=start
        res=origstr+fill*(start-len(origstr))+newpart 
    return res

def fillz(strn, l, fillchar=' '):
    #Returns a string of length l, starting with strn and filled with fillchar
    #If l is <= lenth of strn, return strn
    nfill= l-len(strn)
    if nfill>0:
        return strn+nfill*fillchar
    else:
        return strn

def join(tabell, topos, frompos):
    #for all rows in tabell: if topos is '', move the value in frompos to topos
    #Brukes bl.a. til å merge 260 med 264 i eksport av Marcposter
    tbl=[]
    for rw in tabell:
        new=list(rw)
        if new[topos]=='':
            new[topos]=new[frompos]
            new[frompos]=''
        tbl.append(tuple(new))
    return tbl

