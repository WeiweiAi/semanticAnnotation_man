# add the parent directory to the path
import sys
sys.path.append('..')
from bio_annotator import *

"""
OPB_00592: Chemical amount flow rate
OPB_00593: Chemical amount density flow rate
OPB_00378: Chemical potential
OPB_01058: Membrane potential
OPB_00411: Charge amount
OPB_01624: Ionic charge
OPB_00425: Molar amount of chemical
OPB_00154: Fluid volume
OPB_00340: Concentration of chemical
OPB_01619: Volumnal density of matter
OPB_01238: Charge areal density
OPB_01237: Charge volumetric density


"""

LOCAL = './GLUT2_BG.ttl#'
MODEL_BASE = './GLUT2_BG.cellml#'
annot_editor = Bio_RDF(LOCAL, MODEL_BASE)

local_cytosol={'portionOfCytosol':{'term': 'FMA:66836','type': 'local'}}
local_intercellular_matrix={'intercellular_matrix':{'term': 'FMA:9672','type': 'local'}}
CA_PhysicalEntity(annot_editor, local_cytosol)
CA_PhysicalEntity(annot_editor, local_intercellular_matrix)

local_source_glucose={'glucose_out':{'type': 'local','term': 'CHEBI:4167', 'partOf': 'intercellular_matrix', 'hasProperty': [('GLUT2_BG.q_init_Ai','OPB:00425'),('GLUT2_BG.mu_Ai','OPB:00378')]}}
local_sink_glucose ={'glucose_in':{'type': 'local','term': 'CHEBI:4167', 'partOf': 'portionOfCytosol', 'hasProperty': [('GLUT2_BG.q_init_Ao','OPB:00425'),('GLUT2_BG.mu_Ao','OPB:00378')]}}
transporter={'facilitated_glucose_transporter':{'type': 'local','term': 'UniProt:P11168','partOf': 'membrane'}}
local_process={'D_glucose_transmembrane_transporter_activity': {'type': 'local','term': 'GO:0055056', 'source': [('glucose_out',1)], 'sink': [('glucose_in',1)],
                                                      'mediator': 'facilitated_glucose_transporter', 'hasProperty': [('GLUT2_BG.v_Ai','OPB:00592')]}}

CA_PhysicalEntity(annot_editor, local_source_glucose)
CA_PhysicalEntity(annot_editor, local_sink_glucose)
CA_PhysicalEntity(annot_editor, transporter)
CA_PhysicalProcess(annot_editor, local_process)
# save the rdf graph to a file
annot_editor.serialize('./GLUT2_BG.ttl', format='ttl')

