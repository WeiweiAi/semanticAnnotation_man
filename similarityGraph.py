from sentence_transformers import SentenceTransformer, util
import torch.backends
import torch.backends.mps
import torch
import rdflib
from tqdm import tqdm

import fineTune


BIOBERT = 'FremyCompany/BioLORD-2023' # this model accommodate semantic textual similarity
device = 'gpu' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'

biobert_model = SentenceTransformer(BIOBERT, device=device)
scincl = SentenceTransformer("malteos/scincl")
largemodel = SentenceTransformer('sentence-t5-large')
fineTune_model = SentenceTransformer('output/combine-qualifiers-model', device=device)

# calculate embeddings for each predicate and object


def get_embeddings(g):
    embeddings = {}

    def get_subject_embedding(s):
        s_embeddings = []
        for p, o in g.predicate_objects(subject=s):
            if (p, o) in embeddings:
                s_embeddings += [embeddings[(p,o)]]
            else:
                if not str(o).startswith('file'):  
                    stacked_embeddings = biobert_model.encode([str(p), str(o)], convert_to_tensor=True)
                    p_o_embedding = torch.mean(stacked_embeddings, 0)
                else:
                    o_embedding = get_subject_embedding(o)
                    p_embedding = biobert_model.encode(str(p), convert_to_tensor=True)
                    stacked_embeddings = torch.stack([p_embedding, o_embedding], dim=0)
                    p_o_embedding = torch.mean(stacked_embeddings, 0)
                s_embeddings += [p_o_embedding]
                embeddings[(p,o)] = p_o_embedding
        return torch.mean(torch.stack(s_embeddings, 0), 0)

    subject_embeddings = {str(s).split('/')[-1]:get_subject_embedding(s) for s in tqdm(g.subjects())}
            
    return subject_embeddings

def compare_rdf(G1_embeddings_dict, G2_embeddings_dict):
    g1_keys, g1_embeddings = zip(*G1_embeddings_dict.items())
    g2_keys, g2_embeddings = zip(*G2_embeddings_dict.items())
    
    g1_tensor = torch.stack(g1_embeddings)  # Shape: [len(dict1), embedding_dim]
    g2_tensor = torch.stack(g2_embeddings)  # Shape: [len(dict2), embedding_dim]
    
    print(g1_tensor.shape)
    print(g2_tensor.shape)

    # Compute cosine similarity (matrix multiplication + normalization)
    g1_norm = g1_tensor / g1_tensor.norm(dim=1, keepdim=True)
    g2_norm = g2_tensor / g2_tensor.norm(dim=1, keepdim=True)
    
    # Retrieve top K matches for each entry in dict1
    top_k = 1  # Change to desired number of top matches
    
    for k, e in G1_embeddings_dict.items():
        cos_scores = util.pytorch_cos_sim(e, g2_tensor)[0]
        top_results = torch.topk(cos_scores, top_k)
        print(k)
        for _, (score, idx) in enumerate(zip(top_results[0], top_results[1])):
            print('   ', g2_keys[idx], float(score))

if __name__ == '__main__':
    
    
    g1 = rdflib.Graph()
    g1.parse('./test/GLUT2_rdf.ttl', format='ttl')
    G1_embeddings_dict = get_embeddings(g1)
    g2 = rdflib.Graph()
    g2.parse('./test/SGLT1_rdf.ttl', format='ttl')
    G2_embeddings_dict = get_embeddings(g2)
    print('Comparing embeddings... G1 vs G2')
    compare_rdf(G1_embeddings_dict, G2_embeddings_dict)
    print('Comparing embeddings... G2 vs G1')
    compare_rdf(G2_embeddings_dict, G1_embeddings_dict)
    
    
    