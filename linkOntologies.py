import requests
import rdflib
from sentence_transformers import SentenceTransformer, util
import os
import torch
from interpretGraph import get_last_uri_segment
import json

api_key = "f3265618-0488-40a4-be60-848b7de89142" # BioPortal API key
BIOBERT = 'FremyCompany/BioLORD-2023' # this model accommodate semantic textual similarity
device = 'gpu' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'

biobert_model = SentenceTransformer(BIOBERT, device=device)

def load_json(json_file):
    """
    Load the json file to a dictionary

    Parameters
    ----------
    json_file : str
        The file path of the json file

    Returns
    -------
    comp_dict : dict
        The dictionary of the json file

    """
    with open(json_file) as f:
        comp_dict = json.load(f)
    return comp_dict

def save_json(comp_dict, json_file):
    """
    Save the dictionary to a json file

    Parameters
    ----------
    comp_dict : dict
        The dictionary of the bond graph model
    json_file : str
        The file path of the json file

    Returns
    -------
    None

    side effect
    ------------
    Save the dictionary to a json file

    """
    with open(json_file, 'w') as f:
        json.dump(comp_dict, f,indent=4)

def find_best_matches(target_embedding, embeddings, threshold=0.55, top_k=1):
    """    
    Match a predicate to a role using cosine similarity.
    
    Parameters
    ----------
    target_embedding : str
        The predicate to match.
    embeddings : dict
        A dictionary of embeddings.
    threshold : float, optional
        The threshold for matching. Default is 0.55.
    top_k : int, optional
        The number of top matches to return. Default is 1.
        
    Returns
    -------
    list or None
        The matched keys or None if no match is found.
    """
    g_keys, g_embeddings = zip(*embeddings.items())
    g_tensor = torch.stack(g_embeddings)  
    cos_scores = util.pytorch_cos_sim(target_embedding, g_tensor)[0]
    top_results = torch.topk(cos_scores, top_k)
    best_indices = top_results[1].tolist()[:top_k]
    least_best_score = top_results[0].tolist()[:top_k][-1]
    best_matches = [g_keys[idx] for idx in best_indices]
    if least_best_score < threshold:
        return None
    else:
        return best_matches

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
    if '_' in curie: # opb:OPB_00318 --> OPB:00318
        curie = curie.split(':')[0] + ':' + curie.split('_')[-1]
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

def get_bio_info(uri):
    """
    Get biological information from a URL.
    
    Parameters:
        

    Returns:
        dict: A dictionary containing the biological information.
    """
    if 'uniprot' in str(uri):
        uniprot_id = get_last_uri_segment(uri).split(":")[-1]
        info = get_uniprot_info(uniprot_id)
    else:
        info = lookup_bioportal_term(get_last_uri_segment(uri))
    if 'error' in info:
        print(f"Cannot find biological info for {uri}")
        return None
    else:
        return info['label']

def linkTerms(graph_json):
    
    dict_graph=load_json(graph_json)
    def entity_info (dict_entity):
        if 'term' in dict_entity:
            dict_entity['label']=get_bio_info(dict_entity['term'])
        if 'anatomical_parts'in dict_entity:
            for anatomical_term in dict_entity['anatomical_parts'].keys():
                if 'term' in dict_entity['anatomical_parts'][anatomical_term]:
                    dict_entity['anatomical_parts'][anatomical_term]['label']=get_bio_info(dict_entity['anatomical_parts'][anatomical_term]['term'])
        if 'properties' in dict_entity:
            for prop in dict_entity['properties'].keys():
                if 'term' in dict_entity['properties'][prop]:
                    dict_entity['properties'][prop]['label']=get_bio_info(dict_entity['properties'][prop]['term'])
    if  'physical_processes' in dict_graph:
       for  key, physical_process in dict_graph['physical_processes'].items():
            entity_info(physical_process)
            if 'source' in physical_process:
                for source in physical_process['source'].values():
                    entity_info (source)
            if 'sink' in physical_process:
                for sink in physical_process['sink'].values():
                    entity_info (sink)
            if 'mediator' in physical_process:
                for mediator in physical_process['mediator'].values():
                    entity_info (mediator)
    if 'local_entities' in dict_graph:
        for local_entity in dict_graph['local_entities'].values():
            entity_info(local_entity)
    
    save_json(dict_graph,graph_json)           

def get_embeddings(dict_json):
    def entity_embeddings (dict_entity):
        if 'label' in dict_entity:
            dict_entity['embedding'] = biobert_model.encode(dict_entity['label'], convert_to_tensor=True)
        if 'anatomical_parts'in dict_entity:
            dict_entity['anatomical_parts']['embedding']={}
            for anatomical_term in dict_entity['anatomical_parts'].keys():
                if 'label' in dict_entity['anatomical_parts'][anatomical_term].keys():
                    # Encode the anatomical term using BioBERT
                    anatomical_embedding = biobert_model.encode(dict_entity['anatomical_parts'][anatomical_term]['label'], convert_to_tensor=True)
                    dict_entity['anatomical_parts']['embedding'][anatomical_term] = anatomical_embedding
        if 'properties' in dict_entity:
            dict_entity['properties']['embedding']={}
            for prop in dict_entity['properties'].keys():
                if 'label' in dict_entity['properties'][prop]:
                    prop_embedding = biobert_model.encode(dict_entity['properties'][prop]['label'], convert_to_tensor=True)
                    dict_entity['properties']['embedding'][prop] = prop_embedding
    if  'physical_processes' in dict_json:
        for key, physical_process in dict_json['physical_processes'].items():
            entity_embeddings(physical_process)
            if 'source' in physical_process:
                physical_process['source']['embedding'] = {}
                for key_source,source in physical_process['source'].items():
                    entity_embeddings (source)
                    if 'embedding' not in source:
                        print(f"Warning: No embedding found for source {key_source} in physical process {key}")
                    else:
                        physical_process['source']['embedding'][key_source] = source['embedding']
            if 'sink' in physical_process:
                physical_process['sink']['embedding'] = {}
                for key_sink,sink in physical_process['sink'].items():
                    entity_embeddings (sink)
                    if 'embedding' not in sink:
                        print(f"Warning: No embedding found for sink {key_sink} in physical process {key}")
                    else:
                        physical_process['sink']['embedding'][key_sink] = sink['embedding']
            if 'mediator' in physical_process:
                physical_process['mediator']['embedding'] = {}
                for key_mediator,mediator in physical_process['mediator'].items():
                    entity_embeddings (mediator) 
                    if 'embedding' not in mediator:
                        print(f"Warning: No embedding found for mediator {key_mediator} in physical process {key}")
                    else:
                        physical_process['mediator']['embedding'][key_mediator] = mediator['embedding']                         
    return dict_json

def mapOntologyTerms(composed_json, module_jsons):
    """
    Map ontology terms in a composed JSON file to their corresponding terms in module JSON files.
    
    Parameters:
        composed_json (str): The path to the composed JSON file.
        module_jsons (list): A list of paths to module JSON files.
        
    Returns:
        None
    """
    composed_dict = load_json(composed_json)
    module_dicts_list = [load_json(module_json) for module_json in module_jsons]
    all_processes_embeddings = {}
    # get embeddings for each module
    module_embeddings = {}
    for module_dict in module_dicts_list:
        module_base = module_dict['model_base'].split('/')[-1]
        module_embeddings[module_base] = get_embeddings(module_dict)
        for key, physical_process_embedding in module_embeddings[module_base].get('physical_processes', {}).items():
            if 'embedding' in physical_process_embedding:
                all_processes_embeddings[module_base+key] = physical_process_embedding['embedding']
    # get embeddings for the composed dictionary
    composed_base = composed_dict['model_base'].split('/')[-1]
    composed_embeddings = get_embeddings(composed_dict)    

    for composed_key, physical_process_embedding in composed_embeddings.get('physical_processes', {}).items():
        best_matched_process = None
        if 'embedding' in physical_process_embedding:
            target_embedding = physical_process_embedding['embedding']
            best_matches = find_best_matches(target_embedding, all_processes_embeddings)
            if best_matches:
                module_base = best_matches[0].split('#')[0]+ '#'
                process_key = best_matches[0][len(module_base):]
                best_matched_process = module_embeddings[module_base]['physical_processes'][process_key]
            else:
                best_matched_process = None
                raise ValueError(f"No matching process found for {composed_key} in composed JSON.")
        if best_matched_process and 'properties' in physical_process_embedding and 'properties' in best_matched_process:
            if 'embedding' in physical_process_embedding['properties']:
                for prop_key, prop_embedding in physical_process_embedding['properties']['embedding'].items():
                    target_embedding = prop_embedding
                    best_matches = find_best_matches(target_embedding, best_matched_process['properties']['embedding'])
                    if best_matches:
                        module_prop_key = best_matches[0]
                        physical_process_embedding['properties'][prop_key]['variable'] = module_prop_key
                    else:
                        physical_process_embedding['properties'][prop_key]['variable'] = None
        
        if best_matched_process and 'source' in physical_process_embedding and 'source' in best_matched_process:
            if 'embedding' in physical_process_embedding['source']:
                for source_key, source_embedding in physical_process_embedding['source']['embedding'].items():
                    target_embedding = source_embedding
                    best_matches = find_best_matches(target_embedding, best_matched_process['source']['embedding'])
                    if best_matches:
                        module_source_key = best_matches[0]
                        composed_source = physical_process_embedding['source'][source_key]
                        module_source = best_matched_process['source'][module_source_key]
                        if 'properties' in composed_source and 'properties' in module_source:
                            if 'embedding' in composed_source['properties']:
                                for prop_key, prop_embedding in composed_source['properties']['embedding'].items():
                                    target_embedding = prop_embedding
                                    best_matches = find_best_matches(target_embedding, module_source['properties']['embedding'])
                                    if best_matches:
                                        module_prop_key = best_matches[0]
                                        composed_source['properties'][prop_key]['variable'] = module_prop_key
                                    else:
                                        composed_source['properties'][prop_key]['variable'] = None
                    else:
                        pass
        if best_matched_process and 'sink' in physical_process_embedding and 'sink' in best_matched_process:
            if 'embedding' in physical_process_embedding['sink']:
                for sink_key, sink_embedding in physical_process_embedding['sink']['embedding'].items():
                    target_embedding = sink_embedding
                    best_matches = find_best_matches(target_embedding, best_matched_process['sink']['embedding'])
                    if best_matches:
                        module_sink_key = best_matches[0]
                        composed_sink = physical_process_embedding['sink'][sink_key]
                        module_sink = best_matched_process['sink'][module_sink_key]
                        if 'properties' in composed_sink and 'properties' in module_sink:
                            if 'embedding' in composed_sink['properties']:
                                for prop_key, prop_embedding in composed_sink['properties']['embedding'].items():
                                    target_embedding = prop_embedding
                                    best_matches = find_best_matches(target_embedding, module_sink['properties']['embedding'])
                                    if best_matches:
                                        module_prop_key = best_matches[0]
                                        composed_sink['properties'][prop_key]['variable'] = module_prop_key
                                    else:
                                        composed_sink['properties'][prop_key]['variable'] = None
        if best_matched_process and 'mediator' in physical_process_embedding and 'mediator' in best_matched_process:
            if 'embedding' in physical_process_embedding['mediator']:
                for mediator_key, mediator_embedding in physical_process_embedding['mediator']['embedding'].items():
                    target_embedding = mediator_embedding
                    best_matches = find_best_matches(target_embedding, best_matched_process['mediator']['embedding'])
                    if best_matches:
                        module_mediator_key = best_matches[0]
                        composed_mediator = physical_process_embedding['mediator'][mediator_key]
                        module_mediator = best_matched_process['mediator'][module_mediator_key]
                        if 'properties' in composed_mediator and 'properties' in module_mediator:
                            if 'embedding' in composed_mediator['properties']:
                                for prop_key, prop_embedding in composed_mediator['properties']['embedding'].items():
                                    target_embedding = prop_embedding
                                    best_matches = find_best_matches(target_embedding, module_mediator['properties']['embedding'])
                                    if best_matches:
                                        module_prop_key = best_matches[0]
                                        composed_mediator['properties'][prop_key]['variable'] = module_prop_key
                                    else:
                                        composed_mediator['properties'][prop_key]['variable'] = None    

    def remove_embeddings(obj):
        if isinstance(obj, dict):
            return {k: remove_embeddings(v) for k, v in obj.items() if k != "embedding"}
        elif isinstance(obj, list):
            return [remove_embeddings(v) for v in obj]
        else:
            return obj
    new_composed_json = os.path.splitext(composed_json)[0] + "_linked.json"
    save_json(remove_embeddings(composed_embeddings), new_composed_json)

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
    #xml_file = "./MacKenzie_1996_rdf.xml"  # Replace with your XML file path
   # xml2ttl(xml_file)
    rdf_graph_json_composed = "./test/compose_BG.json"  # Replace with your RDF graph file path
    linkTerms(rdf_graph_json_composed)
    rdf_graph_json_GLUT2 = "./test/GLUT2_BG.json"  # Replace with your RDF graph file path
    linkTerms(rdf_graph_json_GLUT2)
    rdf_graph_json_SGLT1 = "./test/SGLT1_BG.json"  # Replace with your RDF graph file path
    linkTerms(rdf_graph_json_SGLT1)
    mapOntologyTerms(rdf_graph_json_composed, [rdf_graph_json_GLUT2, rdf_graph_json_SGLT1])
    
    
