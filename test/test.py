import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interpretGraph import interpret_rdf_graph
from linkOntologies import linkTerms
#get the current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
rdf_graph_ttl = current_dir+ "/LR-II.ttl"
interpret_rdf_graph(rdf_graph_ttl)
json_file = current_dir + "/LR-II.json"
linkTerms(json_file)