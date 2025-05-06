from pyomexmeta import RDF, eUriType

# Known issues: can not add multiple properties to the same local entity; has to create the same local entity multiple times with different properties.

def CA_PhysicalEntity(annot_editor, dict_physical_entity):
    """
    dict_physical_entity={local_metaid: {term: 'CHEBI:16236', 
        'partOf':'FMA:66836', 'hasPart': 'FMA:66836',                            
        'hasProperty':[('CellML_metaID','OPB:')]}
        }
    """
    for local_metaid, physical_entity in dict_physical_entity.items():
        with annot_editor.new_physical_entity() as local_entity:
            local_entity.about(local_metaid, eUriType.LOCAL_URI)
            if 'term' in physical_entity:
                local_entity.identity(physical_entity['term'])
            if 'partOf' in physical_entity:
                # if the format is 'name:ID' then it is a ontology term
                # if the format is 'ID' then it is a local ID
                if isinstance(physical_entity['partOf'], list):
                    for part in physical_entity['partOf']:
                        if ':' in part:
                            local_entity.is_part_of(part)
                        else:
                            local_entity.is_part_of(part, eUriType.LOCAL_URI)
                elif isinstance(physical_entity['partOf'], str):
                    if ':' in physical_entity['partOf']:
                        local_entity.is_part_of(physical_entity['partOf'])
                    else:
                        local_entity.is_part_of(physical_entity['partOf'], eUriType.LOCAL_URI)
            if 'hasPart' in physical_entity:
                # the format is 'name:ID' and it is a ontology term
                if isinstance(physical_entity['hasPart'], list):
                    for part in physical_entity['hasPart']:
                        local_entity.has_part(part)
                elif isinstance(physical_entity['hasPart'], str):
                    local_entity.has_part(physical_entity['hasPart'])
            if 'hasProperty' in physical_entity:
                for prop in physical_entity['hasProperty']:
                    local_entity.has_property(prop[0],eUriType.MODEL_URI, prop[1])              
    

def CA_PhysicalProcess(annot_editor,dict_physical_process):
    """
    Annotate a CellML model with physical process information.

    dict_physical_process ={processID:{
      'term': 'GO:0004022',
      'source': [(sourceID, multiplier), ...],
      'sink': [(sinkID, multiplier), ...],
      'mediator': mediatorID,
      'hasProperty':[('CellML_metaID','OPB:')]
      }
      }
    """
    # Adding the annotation of the physical process to the rdf graph
    for processID, physical_process in dict_physical_process.items():
        with annot_editor.new_physical_process() as local_process:
            local_process.about(processID, eUriType.LOCAL_URI)
            if 'term' in physical_process:
                local_process.is_version_of(physical_process['term'])
            if 'source' in physical_process:
                for source in physical_process['source']:
                    local_process.add_source(source[0], eUriType.LOCAL_URI, multiplier=source[1])
            if 'sink' in physical_process:
                for sink in physical_process['sink']:
                    local_process.add_sink(sink[0], eUriType.LOCAL_URI, multiplier=sink[1])
            if 'mediator' in physical_process:
                local_process.add_mediator(physical_process['mediator'], eUriType.LOCAL_URI)
            if 'hasProperty' in physical_process:
                for prop in physical_process['hasProperty']:
                    local_process.has_property(prop[0],eUriType.MODEL_URI, prop[1])
        
def CA_EnergyDiff(annot_editor, dict_energy_differential):
    """
    dict_energy_differential= {local_metaid:{
        'term': 'GO:0004022',
        'source': [sourceID, ...],
        'sink': [sinkID, ...],
        'hasProperty':[('CellML_metaID','OPB:')]
    }
    }
    """
    for local_metaid, energy_differential in dict_energy_differential.items():
        with annot_editor.new_energy_diff() as local_energy_differential:
            local_energy_differential.about(local_metaid, eUriType.LOCAL_URI)
            if 'source' in energy_differential:
                for source in energy_differential['source']:
                    local_energy_differential.add_source(source, eUriType.LOCAL_URI)
            if 'sink' in energy_differential:
                for sink in energy_differential['sink']:
                    local_energy_differential.add_sink(sink, eUriType.LOCAL_URI)
            if 'hasProperty' in energy_differential:
                for prop in energy_differential['hasProperty']:
                    local_energy_differential.has_property(prop[0],eUriType.MODEL_URI, prop[1])

def CA_editor(cellmlFile):
    modelname = cellmlFile.split('.cellml')[0]
    annot_rdf = RDF()
    annot_rdf.set_archive_uri(modelname+".omex")
    annot_rdf.set_model_uri(cellmlFile)
    cellml = """
        <model xmlns="http://www.cellml.org/cellml/1.1#" xmlns:cmeta="http://www.cellml.org/metadata/1.0#"
              name="annotation_examples" cmeta:id="annExamples">
          <component name="main">
            <variable cmeta:id="main.Volume" initial_value="100" name="Volume" units="dimensionless" />
            <variable cmeta:id="main.MembraneVoltage" initial_value="-80" name="MembraneVoltage" units="dimensionless" />
            <variable cmeta:id="main.ReactionRate" initial_value="1" name="ReactionRate" units="dimensionless" />
          </component>
        </model>
        """
    annot_editor= annot_rdf.to_editor(cellml, generate_new_metaids=False, sbml_semantic_extraction=False)
    return annot_editor,annot_rdf
            