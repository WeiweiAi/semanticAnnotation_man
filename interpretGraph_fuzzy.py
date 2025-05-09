import json
import rdflib
from sentence_transformers import SentenceTransformer, util
from interpretGraph import find_physical_process, find_local_entities, find_participants, find_stoichiometry, get_id, find_best_matches,parse_ttl_file, \
find_cellml_ids, find_ontology_terms,  resolve_entity, last_uri_segment_to_text, get_last_uri_segment, is_ontology_term
from collections import deque
import os
import torch
from tqdm import tqdm

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

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
            if not is_ontology_term(o) and o not in exclude_nodes and not isinstance(o, rdflib.Literal):
                queue.append(o)

        # Backward traversal: node as object
        for s, p, o in graph.triples((None, None, node)):
            if s not in exclude_nodes:
                subgraph.add((s, p, o))
                if not is_ontology_term(s) and not isinstance(s, rdflib.Literal):
                    queue.append(s)

    return subgraph

def dfs_description(graph, node, visited=None, max_depth=3, depth=0):
    """
    Traverse RDF graph starting from node and collect a textual description.
    Stops if an object is an ontology term or max depth is reached.

    Parameters:
        graph: RDFLib Graph.
        node: RDFLib URIRef or BNode.
        visited: set of visited nodes to avoid cycles.
        max_depth: maximum depth for traversal.
        depth: current depth in the traversal.

    Returns:
        list of strings: textual description of the graph.
    """
    if visited is None:
        visited = set()

    if node in visited or depth > max_depth:
        return []
    visited.add(node)

    description = []
    for pred, obj in graph.predicate_objects(subject=node):
        pred_label = last_uri_segment_to_text(pred)
        obj_label = get_last_uri_segment(obj)
        subj_label = get_last_uri_segment(node)
        description.append(f"{subj_label} {pred_label} {obj_label}")
        # Stop recursion if object is an ontology term
        if not is_ontology_term(obj):
            description.extend(dfs_description(graph, obj, visited, max_depth, depth + 1))

    return description

def get_node_embedding(graph, node):
    """
    Extract text description from DFS and compute sentence embedding.
    """
    lines = dfs_description(graph, node)
    if len(lines) == 0:
        return None
    text = ". ".join(lines)
    embedding = model.encode(text, convert_to_tensor=True)
    return embedding

def interpret_subgraph_fuzzy(graph, local_entity):
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
    cellml_ids= find_cellml_ids(graph)
    if cellml_ids:
        cellml_embeddings={}
        for cellml_id in cellml_ids:
            cellml_embeddings[cellml_id]=get_node_embedding(graph, cellml_id)

    ontology_terms= find_ontology_terms(graph)
    # Find the closest match for the local entity in the graph
    local_entity_embedding = get_node_embedding(graph, local_entity)
    # construct the guess embedding for the local entity
    guess_local_entity_embeddings = {}
    if ontology_terms:
        for ontology_term in ontology_terms:
            if 'OPB' in str(ontology_term):
                continue # don't match OPB terms
            pred_label = 'is'
            obj_label = get_last_uri_segment(ontology_term)
            subj_label = get_last_uri_segment(local_entity)
            text = f"{subj_label} {pred_label} {obj_label}. "
            guess_local_entity_embeddings[ontology_term] = model.encode(text, convert_to_tensor=True)
        if len(guess_local_entity_embeddings) == 0:
            best_match = None
        else:
            best_match = find_best_matches(local_entity_embedding, guess_local_entity_embeddings)

        if best_match is None:
            print(f"Cannot find an ontology term for {local_entity}")
        else:
            subgraph_info['term'] = get_last_uri_segment(best_match[0])   
    property_pairs = {}
    if cellml_ids:
        for cellml_id in cellml_ids:
            guess_cellml_id_embeddings = {}
            for ontology_term in ontology_terms:
                if 'OPB' in str(ontology_term) or 'opb' in str(ontology_term):
                    subj_label = get_last_uri_segment(cellml_id)
                    pred_label = 'is version of'
                    obj_label =  get_last_uri_segment(ontology_term)
                    text_1 = f"{subj_label} {pred_label} {obj_label}. "
                    pred_label = 'is property of'
                    obj_label = get_last_uri_segment(local_entity)
                    text_2 = f"{subj_label} {pred_label} {obj_label}."
                    guess_cellml_id_embeddings[ontology_term] = model.encode(text_1+text_2, convert_to_tensor=True)
            if len(guess_cellml_id_embeddings) == 0:
                print(f"Cannot find an property term for {cellml_id}")
                continue
            best_match = find_best_matches(cellml_embeddings[cellml_id], guess_cellml_id_embeddings)    
            if best_match is None:
                print(f"Cannot find an property term for {cellml_id}")
            else:
                ontology_terms.difference_update(set(best_match)) # remove the best match from the ontology terms
                property_pairs[get_id(cellml_id)] = {}
                property_pairs[get_id(cellml_id)]['term'] = get_last_uri_segment(best_match[0])
    if len(property_pairs) > 0: 
        subgraph_info['properties'] = property_pairs
    
    guess_anatomical_part_embeddings = {}
    if ontology_terms:
        for ontology_term in ontology_terms:
            if 'OPB' in str(ontology_term):
                continue
            subj_label = get_last_uri_segment(local_entity)
            pred_label = 'is part of'
            obj_label = get_last_uri_segment(ontology_term)
            text = f"{subj_label} {pred_label} {obj_label}."
            guess_anatomical_part_embeddings[ontology_term] = model.encode(text, convert_to_tensor=True)
    if len(guess_anatomical_part_embeddings) == 0:
        best_match = None
    else:
        best_match = find_best_matches(local_entity_embedding, guess_anatomical_part_embeddings,0.55, len(guess_anatomical_part_embeddings))
    if best_match is None:
        print(f"Cannot find anatomical part for {local_entity}")
    else:
        subgraph_info['anatomical_parts'] ={}
        for anatomical_part in best_match:
            subgraph_info['anatomical_parts'][get_last_uri_segment(anatomical_part)]={}
    return subgraph_info

def interpret_rdf_graph_fuzzy(rdf_graph_ttl, json_file_name=None):
    """
    Interprets an RDF graph and returns a dictionary containing the extracted information.
    
    Parameters:
        rdf_graph_ttl (str): The RDF graph in Turtle format. The full path to the file is required.

    Returns:
        None

    side effects:
        Saves the extracted information to a JSON file in the same directory as the RDF graph.
    
    """
    graph, json_file_name = parse_ttl_file(rdf_graph_ttl, json_file_name)

    process_nodes = find_physical_process(graph)
    if process_nodes is None:
        return None
    local_entities = find_local_entities(graph)
    knownNodes = set()
    physical_processes = {}
    for process_node in process_nodes:
        real_entity = resolve_entity(graph, process_node)
        process_node_id = get_last_uri_segment(real_entity)
        participants = find_participants(graph, process_node)
        participant_nodes = set()
        for role in participants.keys():
            participant_nodes.update(participants[role])
        subgraph  = extract_subgraph_from_node(graph, real_entity, exclude_nodes=participant_nodes)
        subgraph.serialize(f'./{process_node_id}.ttl',format='turtle')
        physical_processes[process_node_id] = interpret_subgraph_fuzzy(subgraph, real_entity) 
        local_entities.discard(real_entity) # remove the process node from local entities 
        knownNodes.add(real_entity)                  
        for role in participants.keys():
            physical_processes[process_node_id][role] = {}
            for participant_node in participants[role]:                
                participant_node_id = get_last_uri_segment(participant_node)
                subgraph  = extract_subgraph_from_node(graph, participant_node, exclude_nodes=process_node)
                subgraph.serialize(f'./{participant_node_id}.ttl',format='turtle')
                physical_processes[process_node_id][role][participant_node_id] =interpret_subgraph_fuzzy(subgraph, participant_node)
                local_entities.discard(participant_node) # remove the process node from local entities
                knownNodes.add(participant_node)
                stoich = find_stoichiometry(graph, participant_node)
                if stoich:
                    physical_processes[process_node_id][role][participant_node_id]['stoichiometry'] = stoich
                else:
                    physical_processes[process_node_id][role][participant_node_id]['stoichiometry'] = 1.0

    
    for local_entity in local_entities:
        subgraph= extract_subgraph_from_node(graph, local_entity, exclude_nodes=knownNodes)
        physical_processes[get_last_uri_segment(local_entity)] = interpret_subgraph_fuzzy(subgraph, local_entity)
        knownNodes.add(local_entity)

    with open(json_file_name, 'w') as f:
        json.dump(physical_processes, f, indent=4)
    print(f"Extracted information saved to {json_file_name}") 

                                      

if __name__ == "__main__":
    # Example usage
    #xml_file = "./MacKenzie_1996_rdf.xml"  # Replace with your XML file path
   # xml2ttl(xml_file)
    rdf_graph_ttl = "./test/GLUT2_BG.ttl"  # Replace with your RDF graph file path
    interpret_rdf_graph_fuzzy(rdf_graph_ttl, 'GLUT2_BG_fuzzy.json')
    rdf_graph_ttl = "./test/GLUT2_rdf.ttl"  # Replace with your RDF graph file path
    interpret_rdf_graph_fuzzy(rdf_graph_ttl, 'GLUT2_rdf_fuzzy.json')
    rdf_graph_ttl = "./test/SGLT1_rdf.ttl"  # Replace with your RDF graph file path
    interpret_rdf_graph_fuzzy(rdf_graph_ttl, 'SGLT1_rdf_fuzzy.json')
    rdf_graph_ttl = "./test/MacKenzie_1996_rdf.ttl"  # Replace with your RDF graph file path
    interpret_rdf_graph_fuzzy(rdf_graph_ttl, 'MacKenzie_1996_rdf_fuzzy.json')

    
