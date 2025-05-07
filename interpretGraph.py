from logging import warning
import json
import requests
import rdflib
from sentence_transformers import SentenceTransformer, util
import re
from collections import deque
import urllib.parse
import os
from pathlib import PurePath

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')
api_key = "f3265618-0488-40a4-be60-848b7de89142" # BioPortal API key

# Define templates for hybrid matching
ROLE_TEMPLATES = {
    "hasSinkParticipant": "has sink participant",
    "hasSourceParticipant": "has source participant",
    "hasMediatorParticipant": "has mediator participant",
}
ENTITY_TEMPLATES = {
    "hasPhysicalEntityReference": "has physical entity reference",
}
PROPERTY_TEMPLATES = {
    "isPropertyOf": "is property of",
    "hasProperty": "has property",
}

IS_TEMPLATES = {
    "is": "is",
    "isVersionOf": "is version of",
    "hasVersion": "has version",
    "hasPhysicalDefinition": "has physical definition",
    "isComputationalComponentFor": "is computational component for",
}

PART_TEMPLATES = {
    "hasPart": "has part",
    "isPartOf": "is part of",
}

def get_last_url_segment(url): 
    return urllib.parse.unquote(str(url)).split("/")[-1]

def last_url_segment_to_text(url):
    # if there is # in the url, remove it and everything before it
    text = get_last_url_segment(url)
    # Insert space before each capital letter (except at start)
    camel_to_text= re.sub(r'(?<!^)(?=[A-Z])', ' ', text.split("#")[-1])
    # Replace underscores and hyphens with spaces
    snake_to_text = camel_to_text.replace("_", " ").replace("-", " ").replace(":", " ")
    # Remove extra spaces
    return re.sub(r'\s+', ' ', snake_to_text).strip()

def is_cellml_id(uri):
    # may need to be updated for more general cases
    text = get_last_url_segment(uri)
    if ".cellml#" in str(text) or ("#" in str(text) and '.' in str(text).split("#")[-1]):
        return True
    else: 
        return False

def is_ontology_term(uri):
    # may need to be updated for more general cases
    return "identifiers.org" in str(uri) 

def is_local_entity(uri):
    text = get_last_url_segment(uri)
    if "#" in str(text) and not is_cellml_id(uri):
        return True
    else:
        return False

def is_bg_entity(uri):
    text = get_last_url_segment(uri)
    if (".json#" in str(text)):
        return True
    else:
        return False
# Encode templates
def encode_templates(template_dict):
    return {k: model.encode(v) for k, v in template_dict.items()}

role_embeddings = encode_templates(ROLE_TEMPLATES)
entity_embeddings = encode_templates(ENTITY_TEMPLATES)
property_embeddings = encode_templates(PROPERTY_TEMPLATES)
is_embeddings = encode_templates(IS_TEMPLATES)
part_embeddings = encode_templates(PART_TEMPLATES)

# match two sentences using cosine similarity
def match_sentences(s1, s2):
    return util.cos_sim(model.encode(s1), model.encode(s2)).item()
# Hybrid predicate matcher
def match_predicate(pred, embeddings, threshold=0.55):
    """    
    Match a predicate to a role using cosine similarity.
    
    Parameters
    ----------
    pred : str
        The predicate to match.
        embeddings : dict
        A dictionary of predicates and their embeddings.
        threshold : float, optional
        The threshold for matching. Default is 0.55.
        
    Returns
    -------
    str or None
        The matched role or None if no match is found.
    """
    pred_text = last_url_segment_to_text(pred)
    pred_emb = model.encode(pred_text)
    best_match, best_score = None, -1
    for role, emb in embeddings.items():
        score = util.cos_sim(pred_emb, emb).item()
        if score > best_score:
            best_match, best_score = role, score
    return best_match if best_score >= threshold else None

def find_local_entities(g):
    """
    Find local entities in the RDF graph.
    
    Notes: This function searches for subjects and objects that are local entities.
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    
    Returns
    -------
    set or None
        A set of local entity nodes if found, otherwise None.
        
    """
    local_entities = set()
    for s, p, o in g:
        if is_local_entity(s):
            local_entities.add(resolve_entity(g, s))
        if is_local_entity(o):
            local_entities.add(resolve_entity(g, o))
    return local_entities if len(local_entities) > 0 else None

# Helper to find the physical process node (D-glucose transport)
def find_physical_process(g):
    """
    Find the physical process node in the RDF graph.

    Notes: This function searches for subjects that have a predicate semantically matching 
            "has Source Participant", "has Sink Participant", or "has Mediator Participant".
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    
    Returns
    -------
    set or None
        A set of process nodes if found, otherwise None.
        
"""
    process_nodes = set()
    for s, p, o in g:
        role = match_predicate(str(p), role_embeddings)
        if role and ( "Source" in role or "Sink" in role or "Mediator" in role):
            process_nodes.add(s) 
    return process_nodes if len(process_nodes) > 0 else None

# Find participants (source, sink, mediator)
def find_participants(g, process_node):
    """
    Find participants (source, sink, mediator) in the RDF graph.
    
    Notes: This function searches for objects that have a predicate semantically matching 
            "has Source Participant", "has Sink Participant", or "has Mediator Participant".
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    process_node : rdflib.URIRef
        The process node to search for participants.
    
    Returns
    -------
    dict
        A dictionary with keys "source", "sink", and "mediator" containing the sets of respective participant nodes.
    """

    participants = {"source": set(), "sink": set(), "mediator": set()}
    for s, p, o in g.triples((process_node, None, None)):
        role = match_predicate(str(p), role_embeddings)
        if role:
            if "Source" in role:
                participants["source"].add(resolve_entity(g, o))
            elif "Sink" in role:
                participants["sink"].add(resolve_entity(g, o))
            elif "Mediator" in role:
                participants["mediator"].add(resolve_entity(g, o))
    return participants

# Resolve real physical entity
def resolve_entity(g, temp_node):
    """
    Resolve the real physical entity from a temporary node in the RDF graph.
    
    Notes: This function searches for objects that have a predicate semantically matching
            "has Physical Entity Reference".
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    temp_node : rdflib.URIRef
        The temporary node to resolve.
    
    Returns
    -------
    rdflib.URIRef
        The resolved physical entity node if found, otherwise the original temporary node.
    """
    for s, p, o in g.triples((temp_node, None, None)):
        role = match_predicate(str(p), entity_embeddings)
        if role:
            return o
    return temp_node  

# Find stoichiometry
def find_stoichiometry(g, participant_node):
    """
    Find the stoichiometry of a participant in the RDF graph.
    Notes: This function searches for objects that have a predicate "hasMultiplier".
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    participant_node : rdflib.URIRef
        The participant node to find stoichiometry for.
    
    Returns
    -------
    float
        The stoichiometry of the participant if found, otherwise 1.0.
    """
    for s, p, o in g:
        if str(p).endswith("hasMultiplier") and str(s) == str(participant_node):
            return float(o)
        elif str(p).endswith("hasMultiplier") and resolve_entity(g, s) == participant_node:
            return float(o) 
    return 1.0  # default stoichiometry

# Find the anatomical part of the entity
def find_anatomical_part(g,entity_node=None):
    """
    Find the anatomical part of an entity in the RDF graph.
    
    Notes: This function searches for triples with predicates semantically matching "is Part Of" and "has Part".
           If the anatomical part is a local entity, it will be resolved to its ontology term (maximum depth 1).
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    entity_node : rdflib.URIRef, optional
        The entity node to find anatomical part for. If None, search all nodes.
    
    Returns
    -------
    list or None
        A list of anatomical ontology terms if found, otherwise None.
    """
    # Find anatomical part of the entity node
    anatomical_part = []
    def _find_anatomical_part(g, entity_node):
            for s, p, o in g.triples((entity_node, None, None)):
                role = match_predicate(str(p), part_embeddings)
                if role == "isPartOf":
                    if is_local_entity(o):
                        if find_ontology_term(g, o) is not None:
                            anatomical_part.append(find_ontology_term(g, o))
                        elif g.objects(o, None) is not None:
                            _find_anatomical_part(g, o)
                    elif is_ontology_term(o):
                        anatomical_part.append(o)
            for s, p, o in g.triples((None, None, entity_node)):
                role = match_predicate(str(p), part_embeddings)
                if role == "hasPart":
                    if is_local_entity(s):
                        if find_ontology_term(g, s) is not None:
                            anatomical_part.append(find_ontology_term(g, s))
                        elif g.subjects(None, s) is not None:
                            _find_anatomical_part(g, s)
                    elif is_ontology_term(s):
                        anatomical_part.append(s)
    if entity_node:
        _find_anatomical_part(g, entity_node)
    else:
        for s, p, o in g:
            role= match_predicate(str(p), part_embeddings)
            if role == "isPartOf":
                if is_local_entity(o):
                    if find_ontology_term(g, o) is not None:
                        anatomical_part.append(find_ontology_term(g, o))
                elif is_ontology_term(o):
                    anatomical_part.append(o)
            if role == "hasPart":
                if is_local_entity(s):
                    if find_ontology_term(g, s) is not None:
                        anatomical_part.append(find_ontology_term(g, s))
                elif is_ontology_term(s):
                    anatomical_part.append(s)

    return anatomical_part if len(anatomical_part) > 0 else None            
                
# Find properties from entity node if provided, otherwise from all property nodes
def find_properties(g, entity_node=None):
    """
    Find properties of an entity in the RDF graph.
    
    Notes: This function searches for triples with predicates semantically matching "is Property Of" and "has Property".
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    entity_node : rdflib.URIRef, optional
        The entity node to find properties for. If None, search all nodes.
    
    Returns
    -------
    dict or None
        A dictionary with CellML IDs as keys and ontology terms as values if found, otherwise None.
    """
    # Find properties of the entity node
    properties = {} # cellml_id: property
    if entity_node:
        for s, p, o in g.triples((None, None, entity_node)):
            prop_role = match_predicate(str(p), property_embeddings)
            if prop_role == "isPropertyOf" :        
                if is_cellml_id(s):
                    properties[s] = find_ontology_term(g, s)
                elif is_ontology_term(s) :
                    cellml_id= find_cellmlID(g, s)
                    properties[cellml_id] = s
                elif is_local_entity(s): # if the property is a local entity, resolve it to its ontology term
                    cellml_id= find_cellmlID(g, s)
                    if cellml_id is not None:
                        properties[cellml_id] = find_ontology_term(g, s)
        for s, p, o in g.triples((entity_node, None, None)):
            prop_role = match_predicate(str(p), property_embeddings)
            if prop_role == "hasProperty":
                if is_cellml_id(o):
                    properties[o] = find_ontology_term(g, o)
                elif is_ontology_term(o):
                    cellml_id= find_cellmlID(g, o)
                    properties[cellml_id] = o  
                elif is_local_entity(o):
                    cellml_id= find_cellmlID(g, o)
                    if cellml_id is not None:
                        properties[cellml_id] = find_ontology_term(g, o)
    else:
        for s, p, o in g:
            prop_role = match_predicate(str(p), property_embeddings)
            if prop_role == "isPropertyOf" :        
                if is_cellml_id(s):
                    properties[s] = find_ontology_term(g, s)
                elif is_ontology_term(s) :
                    cellml_id= find_cellmlID(g, s)
                    properties[cellml_id] = s
                elif is_local_entity(s):
                    cellml_id= find_cellmlID(g, s)
                    if cellml_id is not None:
                        properties[cellml_id] = find_ontology_term(g, s)
            if prop_role == "hasProperty":
                if is_cellml_id(o):
                    properties[o] = find_ontology_term(g, o)
                elif is_ontology_term(o):
                    cellml_id= find_cellmlID(g, o)
                    properties[cellml_id] = o
                elif is_local_entity(o):
                    cellml_id= find_cellmlID(g, o)
                    if cellml_id is not None:
                        properties[cellml_id] = find_ontology_term(g, o)
                  
    return properties if len(properties) > 0 else None

def find_cellmlID(g, node):
    """
    Find the CellML ID of a node in the RDF graph.
    
    Notes: This function searches for triples with predicates semantically matching "is", "is Version Of", and "has Version".
           The depth-first search is performed in both directions (subject and object).
           The maximum number of CellML IDs found is 1.
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    node : rdflib.URIRef
        The node to find CellML ID for.
    
    Returns
    -------
    str or None
        The CellML ID if found, otherwise None.
    """
    cellml_ids = []
    for s, p, o in g.triples((node, None, None)):
        prop_role = match_predicate(str(p), is_embeddings)
        if prop_role in ["is", "hasVersion"]:
            if is_cellml_id(o):
                cellml_ids.append(o)
            else:
                warning(f"Cannot find a CellML ID for {node}")
    for s, p, o in g.triples((None, None, node)):
        prop_role = match_predicate(str(p), is_embeddings)
        if prop_role in ["is","isVersionOf",'isComputationalComponentFor']:
            if is_cellml_id(s):
                cellml_ids.append(s)
            else:
                warning(f"Cannot find a CellML ID for {node}")
    if len(cellml_ids) > 1:
        raise Exception(f"Multiple CellML IDs found for {node}")
    else:
        cellml_ids = cellml_ids[0] if cellml_ids else None
    return cellml_ids

def find_ontology_term(g, meta_id):
    """
    Find the ontology term for a given meta_id in the RDF graph.
    
    Notes: This function searches for triples with predicates semantically matching "is","is Version Of" and "has Version".
            The depth-first search is performed in both directions (subject and object). The maximum depth is 1.
            The maximum number of ontology terms found is 1. TODO: may need to be updated for more general cases.
    
    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph to search.
    meta_id : rdflib.URIRef
        The meta_id to find ontology term for.
    
    Returns
    -------
    rdflib.URIRef or None
        The ontology term if found, otherwise None.
    """
    ontology_term = []
    for s, p, o in g.triples((meta_id, None, None)):
        prop_role = match_predicate(str(p), is_embeddings)
        if prop_role in ["is", "isVersionOf",'hasPhysicalDefinition']:
            if is_ontology_term(o):
                ontology_term.append(o)
            else:
                warning(f"Cannot find an ontology term for {meta_id}")
    for s, p, o in g.triples((None, None, meta_id)):
        prop_role = match_predicate(str(p), is_embeddings)
        if prop_role in ["is","hasVersion"]:
            if is_ontology_term(s):
                ontology_term.append(s)
            else:
                warning(f"Cannot find an ontology term for {meta_id}")
    if len(ontology_term) > 1:
        raise Exception(f"Multiple ontology terms found for {meta_id}")
    else:
        ontology_term = ontology_term[0] if ontology_term else None
    return ontology_term

def extract_subgraph_from_node(graph, start_node, exclude_nodes=None):
    """
    Traverses RDF graph from start_node in both directions, stops at ontology terms.

    Parameters:
        graph: RDFLib Graph.
        start_node: RDFLib URIRef or BNode.
        exclude_nodes: set of nodes to exclude from traversal.

    Returns:
        RDFLib Graph: subgraph connected to the start_node.
    """
    visited = set()
    queue = deque([start_node])
    subgraph = rdflib.Graph()
    exclude_nodes = exclude_nodes or set()

    while queue:
        node = queue.popleft()
        if node in visited or node in exclude_nodes:
            continue
        visited.add(node)

        # Forward traversal: node as subject
        for s, p, o in graph.triples((node, None, None)):
            subgraph.add((s, p, o))
            if not is_ontology_term(o) and o not in exclude_nodes:
                queue.append(o)

        # Backward traversal: node as object
        for s, p, o in graph.triples((None, None, node)):
            if s not in exclude_nodes:
                subgraph.add((s, p, o))
                if not is_ontology_term(s):
                    queue.append(s)

    return subgraph

def get_uniprot_info(uniprot_id: str) -> dict:
    """Retrieve protein name and organism from UniProt ID.
       # Example usage
        info = get_uniprot_info("P11168")
        print(info)
    
    """
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.json"
    response = requests.get(url)
    
    if response.ok:
        data = response.json()
        protein_name = data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value")
        organism = data.get("organism", {}).get("scientificName")
        return {
            "uniprot_id": uniprot_id,
            "label": protein_name,
            "organism": organism
        }
    else:
        return {"error": f"Failed to retrieve data for {uniprot_id}"}

import requests

def lookup_bioportal_term(curie: str, api_key=api_key):
    """
    Perform a general BioPortal search for a given CURIE (e.g., 'GO:0055056').
    print(lookup_bioportal_term("GO:0055056", api_key))
    print(lookup_bioportal_term("CHEBI:4167", api_key))
    print(lookup_bioportal_term("FMA:66836", api_key))
    print(lookup_bioportal_term("OPB:00378", api_key))

    Returns:
        A dictionary with label, definition, synonyms, and ID if found.
    """
    if '_' in curie:
        curie = curie.replace("_", ":")
    url = "https://data.bioontology.org/search"
    params = {
        "q": curie,
        "require_exact_match": "true"
    }
    headers = {
        "Authorization": f"apikey token={api_key}"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.ok:
        data = response.json()
        if data.get("collection"):
            entry = data["collection"][0]
            return {
                "label": entry.get("prefLabel", ""),
                "definition": entry.get("definition", []),
                "synonyms": entry.get("synonym", []),
                "id": entry.get("@id", ""),
                "ontology": entry.get("links", {}).get("ontology", "")
            }
        else:
            return {"error": "No match found"}
    else:
        return {
            "error": "Lookup failed",
            "status_code": response.status_code,
            "reason": response.reason,
            "text": response.text
        }

# Example usage:

def interpret_subgraph(graph, local_entity):
    """
    Interprets an RDF graph and returns a dictionary containing the extracted information.
    
    Parameters:
        graph (rdflib.Graph): The RDF graph to interpret.
        local_entity (rdflib.URIRef): The local entity to extract information for.

    Returns:
        None

    side effects:
        Saves the extracted information to a JSON file in the same directory as the RDF graph.
    
    """
    subgraph_info = {}
    subgraph_info['label'] = ''
    what_entity = find_ontology_term(graph, local_entity)
    if what_entity is None:
        print(f"Cannot find an ontology term for {local_entity}")
    else:
        if 'uniprot' in str(what_entity):
            uniprot_id = get_last_url_segment(what_entity).split(":")[-1]
            info = get_uniprot_info(uniprot_id)
        else:
            info = lookup_bioportal_term(get_last_url_segment(what_entity))
        if 'error' in info:
            print(f"Cannot find biological info for {local_entity}")
        else:
            subgraph_info['label'] = info['label']
            properties = find_properties(graph, local_entity)
            if properties:
                subgraph_info['properties'] = {}
                for cellml_id, prop in properties.items():
                    physicsal_property = lookup_bioportal_term(get_last_url_segment(prop))
                    if 'error' in physicsal_property:
                         print(f"Cannot find physicsal property for {prop}")
                         subgraph_info['properties'][get_last_url_segment(cellml_id)] = ''
                    else:
                        subgraph_info['properties'][get_last_url_segment(cellml_id)] = physicsal_property['label']
            anatomical_parts= find_anatomical_part(graph, local_entity)
            if anatomical_parts is None:
                print(f"Cannot find anatomical part for {local_entity}")
            else:
                subgraph_info['anatomical_parts'] =[]
                for anatomical_part in anatomical_parts:
                    if 'uniprot' in str(anatomical_part):
                        uniprot_id = get_last_url_segment(anatomical_part).split(":")[-1]
                        info = get_uniprot_info(uniprot_id)
                    else:
                        info = lookup_bioportal_term(get_last_url_segment(anatomical_part))                                
                    if 'error' in info:
                        print(f"Cannot find anatomical part for {anatomical_part}")
                        subgraph_info['anatomical_parts'].append('')
                    else:
                        subgraph_info['anatomical_parts'].append(info['label'])
    return subgraph_info

def interpret_rdf_graph(rdf_graph_ttl):
    """
    Interprets an RDF graph and returns a dictionary containing the extracted information.
    
    Parameters:
        rdf_graph_ttl (str): The RDF graph in Turtle format. The full path to the file is required.

    Returns:
        None

    side effects:
        Saves the extracted information to a JSON file in the same directory as the RDF graph.
    
    """
    # Load the RDF graph
    graph = rdflib.Graph()
    json_file_name = PurePath(rdf_graph_ttl).name.split(".")[0] + ".json"
    if os.path.isabs(rdf_graph_ttl):
        graph.parse(rdf_graph_ttl, format='ttl')
        # get the folder name using PurePath
        file_path = PurePath(rdf_graph_ttl).parent
    else:
        # get the absolute path of the current file
        full_path=os.path.join(os.path.dirname(__file__), rdf_graph_ttl)
        graph.parse(full_path, format='ttl')
        # get the folder name using PurePath
        file_path = PurePath(full_path).parent
    
    json_file_name = os.path.join(file_path, json_file_name)

    process_nodes = find_physical_process(graph)
    if process_nodes is None:
        return None
    local_entities = find_local_entities(graph)
    physical_processes = {}
    for process_node in process_nodes:
        real_entity = resolve_entity(graph, process_node)
        process_node_id = get_last_url_segment(real_entity)
        physical_processes[process_node_id] = interpret_subgraph(graph, real_entity) 
        local_entities.discard(real_entity) # remove the process node from local entities              
        participants = find_participants(graph, process_node)
        for role in participants.keys():
            physical_processes[process_node_id][role] = {}
            for participant_node in participants[role]:                
                participant_node_id = get_last_url_segment(participant_node)
                physical_processes[process_node_id][role][participant_node_id] =interpret_subgraph(graph, participant_node)
                local_entities.discard(participant_node) # remove the process node from local entities
                stoich = find_stoichiometry(graph, participant_node)
                if stoich:
                    physical_processes[process_node_id][role][participant_node_id]['stoichiometry'] = stoich
                else:
                    physical_processes[process_node_id][role][participant_node_id]['stoichiometry'] = 1.0
    
    if local_entities is not None:
        for local_entity in local_entities:
            if not find_properties(graph, local_entity):
                node_id = get_last_url_segment(local_entity)
                physical_processes[node_id] = interpret_subgraph(graph, local_entity)

    with open(json_file_name, 'w') as f:
        json.dump(physical_processes, f, indent=4)
    print(f"Extracted information saved to {json_file_name}") 
    
def xml2ttl(xml_file):
    """
    Convert an XML file to Turtle format and save it as a TTL file.
    
    Parameters:
        xml_file (str): The path to the XML file.
        ttl_file (str): The path to save the converted TTL file.
    
    Returns:
        None
    """
    graph = rdflib.Graph()
    graph.parse(xml_file, format='xml')
    ttl_file = os.path.splitext(xml_file)[0] + ".ttl"
    graph.serialize(destination=ttl_file, format='turtle')                                        

if __name__ == "__main__":
    # Example usage
    xml_file = "./MacKenzie_1996_rdf.xml"  # Replace with your XML file path
    xml2ttl(xml_file)
    rdf_graph_ttl = "./MacKenzie_1996_rdf.ttl"  # Replace with your RDF graph file path
    interpret_rdf_graph(rdf_graph_ttl)
    
