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

LOCAL = './compose_BG.ttl#'
MODEL_BASE = './compose_BG_refine.json#'
annot_editor = Bio_RDF(LOCAL, MODEL_BASE)

local_cytosol={'portionOfCytosol':{'term': 'FMA:66836','type': 'local'}}
local_intercellular_matrix={'intercellular_matrix':{'term': 'FMA:9672','type': 'local'}}
local_membrane={'membrane':{'term': 'GO:0005886','type': 'local'}}
CA_PhysicalEntity(annot_editor, local_cytosol)
CA_PhysicalEntity(annot_editor, local_intercellular_matrix)
CA_PhysicalEntity(annot_editor, local_membrane)
local_source_glucose={'Glco':{'type': 'model','term': 'CHEBI:4167', 'partOf': 'intercellular_matrix', 'hasProperty': ['OPB:00425','OPB:00378']}}
local_sink_glucose ={'Glci':{'type': 'model','term': 'CHEBI:4167', 'partOf': 'portionOfCytosol', 'hasProperty': ['OPB:00425','OPB:00378']}}
local_source_Na={'Nao':{'type': 'model','term': 'CHEBI:29101', 'partOf': 'intercellular_matrix', 'hasProperty': ['OPB:00425','OPB:00378']}}
local_sink_Na ={'Nai':{'type': 'model','term': 'CHEBI:29101', 'partOf': 'portionOfCytosol', 'hasProperty': ['OPB:00425','OPB:00378']}}
transporter_GLUT2={'GLUT2':{'type': 'local','term': 'UniProt:P11168','partOf': 'membrane'}}
local_process_GLUT2={'GLUT2': {'type': 'model','term': 'GO:0055056','source': [('model', 'Glco',1)], 'sink': [('model','Glci',1)],
                                                      'mediator': ('local', 'GLUT2'), 'hasProperty': ['OPB:00592']}}

transporter_SGLT1={'SGLT1': {'type': 'local','term': 'UniProt:P13866','partOf': 'membrane'}}
local_process_SGLT1={'SGLT1': {'type': 'model','term': 'GO:0005412','source': [('model', 'Glco',1),('model','Nao',2)],
                                                      'sink': [('model','Glci',1),('model','Nai',2)],
                                                      'mediator': ('local', 'SGLT1'), 'hasProperty': ['OPB:00592']}}

CA_PhysicalEntity(annot_editor, local_source_glucose)
CA_PhysicalEntity(annot_editor, local_sink_glucose)
CA_PhysicalEntity(annot_editor, local_source_Na)
CA_PhysicalEntity(annot_editor, local_sink_Na)
CA_PhysicalEntity(annot_editor, transporter_GLUT2)
CA_PhysicalEntity(annot_editor, transporter_SGLT1)
CA_PhysicalProcess(annot_editor, local_process_GLUT2)
CA_PhysicalProcess(annot_editor, local_process_SGLT1)

# save the rdf graph to a file
annot_editor.serialize('./compose_BG.ttl', format='ttl')

