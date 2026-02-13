# add the parent directory to the path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bio_annotator import *

"""
OPB_00592: Chemical amount flow rate
OPB_00593: Chemical amount density flow rate
OPB_00318: Charge flow rate
OPB_00299: Fluid flow rate

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
current_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL = './SGLT1_BG_annotated.ttl#'
MODEL_BASE = './SGLT1_BG_annotated.cellml#'
annot_editor = Bio_RDF(LOCAL, MODEL_BASE)

local_cytosol={'portionOfCytosol':{'term': 'FMA:66836','type': 'local'}}
local_intercellular_matrix={'intercellular_matrix':{'term': 'FMA:9672','type': 'local'}}
local_membrane={'membrane':{'term': 'GO:0005886','type': 'local'}}
CA_PhysicalEntity(annot_editor, local_cytosol)
CA_PhysicalEntity(annot_editor, local_intercellular_matrix)

local_sink_glucose={'glucose_in':{'type': 'local','term': 'CHEBI:4167', 'partOf': 'portionOfCytosol', 'hasProperty': [('b4dab3','OPB:00425'),('b4dad0','OPB:00378')]}}
local_source_glucose ={'glucose_out':{'type': 'local','term': 'CHEBI:4167', 'partOf': 'intercellular_matrix', 'hasProperty': [('b4dab5','OPB:00425'),('b4dad1','OPB:00378')]}}

local_sink_Na={'Na_in':{'type': 'local','term': 'CHEBI:29101', 'partOf': 'portionOfCytosol', 'hasProperty': [('b4daaf','OPB:00425'),('b4dace','OPB:00378')]}}
local_source_Na ={'Na_out':{'type': 'local','term': 'CHEBI:29101', 'partOf': 'intercellular_matrix', 'hasProperty': [('b4dab1','OPB:00425'),('b4dacf','OPB:00378')]}}

transporter={'Sodium_glucose_cotransporter_1':{'type': 'local','term': 'UniProt:P13866','partOf': 'membrane'}}
local_process={'D-glucose_sodium_symporter_activity': {'type': 'local','term': 'GO:0005412', 'source': [('local','glucose_out',1),('local','Na_out',2)], 'sink': [('local','glucose_in',1),('local','Na_in',2)],
                                                      'mediator': ('local','Sodium_glucose_cotransporter_1'), 'hasProperty': [('b4daf3','OPB:00592')]}}

CA_PhysicalEntity(annot_editor, local_source_glucose)
CA_PhysicalEntity(annot_editor, local_sink_glucose)
CA_PhysicalEntity(annot_editor, local_source_Na)
CA_PhysicalEntity(annot_editor, local_sink_Na)

CA_PhysicalEntity(annot_editor, transporter)
CA_PhysicalProcess(annot_editor, local_process)

annot_editor.serialize(current_dir + '/SGLT1_BG_annotated.ttl', format='ttl')

