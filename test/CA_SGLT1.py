# add the parent directory to the path
import sys
sys.path.append('..')
from annotation_CA import *

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

annot_editor,annot_rdf = CA_editor("SGLT1_BG.cellml")

local_cytosol={'portionOfCytosol':{'term': 'FMA:66836'}}
local_intercellular_matrix={'intercellular_matrix':{'term': 'FMA:9672'}}
local_membrane={'membrane':{'term': 'GO:0005886'}}
CA_PhysicalEntity(annot_editor, local_cytosol)
CA_PhysicalEntity(annot_editor, local_intercellular_matrix)

local_source_glucose={'glucose_out':{'term': 'CHEBI:4167', 'partOf': 'intercellular_matrix', 'hasProperty': [('SGLT1_BG.q_Glci','OPB:00425')]}}
local_sink_glucose ={'glucose_in':{'term': 'CHEBI:4167', 'partOf': 'portionOfCytosol', 'hasProperty': [('SGLT1_BG.q_Glco','OPB:00425')]}}

local_source_Na={'Na_out':{'term': 'CHEBI:29101', 'partOf': 'intercellular_matrix', 'hasProperty': [('SGLT1_BG.q_Nai','OPB:00425')]}}
local_sink_Na ={'Na_in':{'term': 'CHEBI:29101', 'partOf': 'portionOfCytosol', 'hasProperty': [('SGLT1_BG.q_Nao','OPB:00425')]}}

local_source_glucose_2={'glucose_out':{'term': 'CHEBI:4167', 'partOf': 'intercellular_matrix', 'hasProperty': [('SGLT1_BG.mu_Glci','OPB:00378')]}}
local_sink_glucose_2 ={'glucose_in':{'term': 'CHEBI:4167', 'partOf': 'portionOfCytosol', 'hasProperty': [('SGLT1_BG.mu_Glco','OPB:00378')]}}

local_source_Na_2={'Na_out':{'term': 'CHEBI:29101', 'partOf': 'intercellular_matrix', 'hasProperty': [('SGLT1_BG.mu_Nai','OPB:00378')]}}
local_sink_Na_2 ={'Na_in':{'term': 'CHEBI:29101', 'partOf': 'portionOfCytosol', 'hasProperty': [('SGLT1_BG.mu_Nao','OPB:00378')]}}

transporter={'Sodium_glucose_cotransporter_1':{'term': 'UniProt:P13866','partOf': 'membrane'}}
local_process={'D-glucose_sodium_symporter_activity': {'term': 'GO:0005412', 'source': [('glucose_out',1),('Na_out',2)], 'sink': [('glucose_in',1),('Na_in',2)],
                                                      'mediator': 'Sodium_glucose_cotransporter_1', 'hasProperty': [('SGLT1_BG.v_r2','OPB:00592')]}}
local_process_2={'D-glucose_sodium_symporter_activity': {'term': 'GO:0005412', 'source': [('glucose_out',1),('Na_out',2)], 'sink': [('glucose_in',1),('Na_in',2)],
                                                      'mediator': 'Sodium_glucose_cotransporter_1', 'hasProperty': [('SGLT1_BG.Ii','OPB:00318')]}}

local_process_ion={'D-glucose_sodium_symporter_activity': {'term': 'GO:0035725', 'source': [('Na_out',2)], 'sink': [('Na_in',2)],
                                                      'mediator': 'Sodium_glucose_cotransporter_1', 'hasProperty': [('SGLT1_BG.Ii','OPB:00318')]}}

local_energyDifferential={'membranePotential': {'source': ['Na_in'], 'sink': ['Na_out'],'hasProperty': [('SGLT1_BG.V0_Vm','OPB:01058')]}}

CA_PhysicalEntity(annot_editor, local_source_glucose)
CA_PhysicalEntity(annot_editor, local_sink_glucose)
CA_PhysicalEntity(annot_editor, local_source_Na)
CA_PhysicalEntity(annot_editor, local_sink_Na)

CA_PhysicalEntity(annot_editor, local_source_glucose_2)
CA_PhysicalEntity(annot_editor, local_sink_glucose_2)

CA_PhysicalEntity(annot_editor, local_source_Na_2)
CA_PhysicalEntity(annot_editor, local_sink_Na_2)

CA_PhysicalEntity(annot_editor, transporter)
CA_PhysicalProcess(annot_editor, local_process)
CA_PhysicalProcess(annot_editor, local_process_2)
CA_EnergyDiff(annot_editor, local_energyDifferential)
annot_rdf.to_file("SGLT1_rdf.ttl",'turtle')
print(annot_rdf)
annot_rdf.draw("SGLT1_rdf")

