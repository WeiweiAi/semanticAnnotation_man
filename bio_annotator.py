from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, FOAF,  DCTERMS, XSD

class Bio_RDF(Graph):
    """ A class to store RDF triples for a Biological models

    Defines the namespaces (https://doi.org/10.1515/jib-2021-0020) 
    and the RDF graph object.

    Attributes
    ----------
    ORCID: Namespace
        The ORCID namespace
    BQMODEL: Namespace
        The BioModels model qualifiers namespace
    BQBIOL: Namespace
        The BioModels biology qualifiers namespace
    PUBMED: Namespace
        The PubMed namespace
    NCBI_TAXONOMY: Namespace
        The NCBI Taxonomy namespace
    BIOMOD: Namespace
        The BioModels database namespace
    CHEBI: Namespace
        The ChEBI namespace
    UNIPROT: Namespace
        The UniProt namespace
    OPB: Namespace
        The Ontology of Physics for Biology namespace
    FMA: Namespace
        The Foundational Model of Anatomy namespace
    GO: Namespace
        The Gene Ontology namespace, https://geneontology.org/docs/ontology-documentation/
    SEMSIM: Namespace
        The SemSim namespace
    prefix_NAMESPACE_: dict
        The dictionary of namespace bindings

    Inherits
    --------
    rdflib.Graph

    Initialization
    --------------
    Bio_RDF(LOCAL, MODEL_BASE)

    Parameters
    ----------
    LOCAL: string
        The local namespace is the namespace of the RDF file
        e.g., Namespace('./'+file_withoutSuffix + '.ttl#') 
    MODEL_BASE: string
        The model base namespace,
        e.g., Namespace('./'+file_withoutSuffix + '.cellml#')
    
    Returns 
    -------
    Bio_RDF
        The Bio_RDF instance

    """
    ORCID = Namespace('http://orcid.org/')   
    BQMODEL = Namespace('http://biomodels.net/model-qualifiers/')
    BQBIOL = Namespace('http://biomodels.net/biology-qualifiers/')
    PUBMED = Namespace('http://identifiers.org/pubmed:')
    NCBI_TAXONOMY = Namespace('http://identifiers.org/taxonomy:')
    BIOMOD = Namespace('http://identifiers.org/biomodels.db:')
    CHEBI = Namespace('http://identifiers.org/CHEBI:')
    UNIPROT = Namespace('http://identifiers.org/uniprot:')
    OPB = Namespace('http://identifiers.org/opb:')
    FMA = Namespace('http://identifiers.org/FMA:')
    GO = Namespace('http://identifiers.org/GO:')
    SEMSIM = Namespace('http://bime.uw.edu/semsim/')
    prefix_NAMESPACE_ = {'rdf':RDF,'foaf':FOAF,'dcitems':DCTERMS, 'orcid':ORCID, 'bqmodel':BQMODEL,'bqbiol':BQBIOL, 'pubmed':PUBMED,'NCBI_Taxon':NCBI_TAXONOMY,
                        'biomod':BIOMOD, 'chebi':CHEBI,'uniprot':UNIPROT,'opb':OPB,'fma':FMA,'go':GO, 'semsim':SEMSIM}
           
    def __init__(self, LOCAL, MODEL_BASE):
        # output: a RDF graph object 
        super().__init__()

        self.prefix_NAMESPACE = Bio_RDF.prefix_NAMESPACE_|{'local':Namespace(LOCAL),'model_base':Namespace(MODEL_BASE)}
        # Defined Namespace bindings.
        for prefix, namespace in self.prefix_NAMESPACE.items():
            self.bind(prefix, namespace)

    def bindNamespace(self, prefix,namespace):
        """ Bind a namespace to the RDF graph object

        Parameters
        ----------
        prefix: string
            The prefix of the namespace
        namespace: Namespace
            The namespace to be binded
        """
        self.prefix_NAMESPACE[prefix] = namespace
        self.bind(prefix, namespace)

    def localNode(self, localitem):
        """ Get the local node of a RDF triple

        Parameters
        ----------
        localitem: string
            The local item of a RDF triple

        Returns
        -------
        URIRef
            The local source of a RDF triple
        """
        return self.prefix_NAMESPACE['local'][localitem]
    
    def modelBaseNode(self, modelBaseItem):
        """ Get the model base node of a RDF triple

        Parameters
        ----------
        modelBaseitem: string
            The model base item of a RDF triple

        Returns
        -------
        URIRef
            The model base source of a RDF triple
        """

        return self.prefix_NAMESPACE['model_base'][modelBaseItem]
    
    def literalNode(self, literalitem, literalType=float):
        """ Get the literal node of a RDF triple

        Parameters
        ----------
        literalitem: string
            The literal item of a RDF triple
        literalType: type
            The type of the literal item

        Returns
        -------
        Literal
            The literal source of a RDF triple
        """
        return Literal(literalitem, datatype=XSD[literalType])
    
    def ontologyNode(self, item):
        """ Get the ontology node of a RDF triple

        Parameters
        ----------
        namespace_prefix: string
            The prefix of an ontology namespace or the local namespace
        item: string, namespace_prefix:id
            The ontology item or the local item

        Raises
        ------
        ValueError
            If the namespace prefix is not found in the Bio_RDF instance
        
        Returns
        -------
        URIRef
            The ontology source of a RDF triple
        """
        namespace_prefix, item = item.split(':')
        if namespace_prefix.lower() in self.prefix_NAMESPACE:
            return self.prefix_NAMESPACE[namespace_prefix.lower()][item]
        else:
            raise ValueError('Namespace prefix not found: '+namespace_prefix) 

def CA_PhysicalEntity(bio_rdf, dict_physical_entity):
    """ Annotate a CellML model with physical entity information.

    Parameters
    ----------
    bio_rdf: Bio_RDF
        The Bio_RDF instance
    dict_physical_entity: dict
        The dictionary of the physical entity, e.g.,
        {'local_metaid': {term: 'CHEBI:16236', type: 'local' or 'model',
            'partOf':'FMA:66836', 'hasPart': 'FMA:66836',                            
            'hasProperty':[('CellML_metaID','OPB:')]}
        }

    Returns 
    -------
    None

    side effects
    ------------
    Adds RDF triples to the Bio_RDF instance

    """
    for local_metaid, physical_entity in dict_physical_entity.items():
        if physical_entity['type'] == 'local':
            model_subj = bio_rdf.localNode(local_metaid)
        elif physical_entity['type'] == 'model':
            model_subj = bio_rdf.modelBaseNode(local_metaid)
        if 'term' in physical_entity:
            pred=bio_rdf.prefix_NAMESPACE['bqbiol']['is']
            ontology_obj = bio_rdf.ontologyNode(physical_entity['term'])
            bio_rdf.add((model_subj, pred, ontology_obj))
        if 'partOf' in physical_entity:
            # if the format is 'name:ID' then it is a ontology term
            # if the format is 'ID' then it is a local ID
            if isinstance(physical_entity['partOf'], list):
                for part in physical_entity['partOf']:
                    if ':' in part:
                        bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isPartOf'], bio_rdf.ontologyNode(part)))
                    else:
                        bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isPartOf'], bio_rdf.localNode(part)))
            elif isinstance(physical_entity['partOf'], str):
                if ':' in physical_entity['partOf']:
                    bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isPartOf'], bio_rdf.ontologyNode(physical_entity['partOf'])))
                else:
                    bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isPartOf'], bio_rdf.localNode(physical_entity['partOf'])))
        if 'hasPart' in physical_entity:
            # the format is 'name:ID' and it is a ontology term
            if isinstance(physical_entity['hasPart'], list):
                for part in physical_entity['hasPart']:
                    bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasPart'], bio_rdf.ontologyNode(part)))
            elif isinstance(physical_entity['hasPart'], str):
                bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasPart'], bio_rdf.ontologyNode(physical_entity['hasPart'])))
        if 'hasProperty' in physical_entity:
            for prop in physical_entity['hasProperty']:
                if isinstance(prop, tuple) and len(prop) == 2: # the property is a tuple of (cellml_metaid, OPB:ID)
                    cellml_metaid = prop[0]
                    propertyTerm= prop[1]
                    cellml_subj = bio_rdf.modelBaseNode(cellml_metaid)
                    bio_rdf.add((cellml_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isPropertyOf'], model_subj))
                    bio_rdf.add((cellml_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isVersionOf'], bio_rdf.ontologyNode(propertyTerm)))
                elif isinstance(prop, str): # the property is a single OPB:ID
                    bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasProperty'], bio_rdf.ontologyNode(prop)))
                else:
                    raise ValueError('The property should be a tuple of (cellml_metaid, OPB:ID) or a single OPB:ID')
 
def CA_PhysicalProcess(bio_rdf, dict_physical_process):
    """ Annotate a CellML model with physical process information.

    Parameters
    ----------
    bio_rdf: Bio_RDF
        The Bio_RDF instance
    dict_physical_process: dict
        The dictionary of the physical process, e.g.,
        {'processID':{ 'type': 'local' or 'model',
            'term': 'GO:0004022',
            'source': [(sourceID, multiplier), ...],
            'sink': [(sinkID, multiplier), ...],
            'mediator': mediatorID,
            'hasProperty':[('CellML_metaID','OPB:')]
            }
        }

    Returns 
    -------
    None

    side effects
    ------------
    Adds RDF triples to the Bio_RDF instance

    """
    for processID, physical_process in dict_physical_process.items():
        if physical_process['type'] == 'local':
            model_subj = bio_rdf.localNode(processID)
        elif physical_process['type'] == 'model':
            model_subj = bio_rdf.modelBaseNode(processID)
        if 'term' in physical_process:
            pred=bio_rdf.prefix_NAMESPACE['bqbiol']['is']
            ontology_obj = bio_rdf.ontologyNode(physical_process['term'])
            bio_rdf.add((model_subj, pred, ontology_obj))
        if 'source' in physical_process:
            for source in physical_process['source']:
                if source[0] == 'local':
                    source_obj = bio_rdf.localNode(source[1])
                elif source[0] == 'model':
                    source_obj = bio_rdf.modelBaseNode(source[1])
                bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasSourceParticipant'], source_obj))
                bio_rdf.add((source_obj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasMultiplier'], bio_rdf.literalNode(str(source[2]), 'float')))
        if 'sink' in physical_process:
            for sink in physical_process['sink']:
                if sink[0] == 'local':
                    sink_obj = bio_rdf.localNode(sink[1])
                elif sink[0] == 'model':
                    sink_obj = bio_rdf.modelBaseNode(sink[1])
                bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasSinkParticipant'], sink_obj))
                bio_rdf.add((sink_obj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasMultiplier'], bio_rdf.literalNode(str(sink[2]), 'float')))
        if 'mediator' in physical_process:
            if physical_process['mediator'][0] == 'local':
                mediator_obj = bio_rdf.localNode(physical_process['mediator'][1])
            elif physical_process['mediator'][0] == 'model':
                mediator_obj = bio_rdf.modelBaseNode(physical_process['mediator'][1])
            bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasMediatorParticipant'], mediator_obj))
        if 'hasProperty' in physical_process:
            for prop in physical_process['hasProperty']:
                if isinstance(prop, tuple) and len(prop) == 2:
                    cellml_metaid = prop[0]
                    propertyTerm= prop[1]
                    cellml_subj = bio_rdf.modelBaseNode(cellml_metaid)
                    bio_rdf.add((cellml_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isPropertyOf'], model_subj))
                    bio_rdf.add((cellml_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['isVersionOf'], bio_rdf.ontologyNode(propertyTerm)))
                elif isinstance(prop, str): # the property is a single OPB:ID
                    bio_rdf.add((model_subj, bio_rdf.prefix_NAMESPACE['bqbiol']['hasProperty'], bio_rdf.ontologyNode(prop)))
                else:
                    raise ValueError('The property should be a tuple of (cellml_metaid, OPB:ID) or a single OPB:ID')

if __name__ == '__main__':
    LOCAL = './test_bg.ttl#'
    MODEL_BASE = './bg.json#'
    bio_rdf = Bio_RDF(LOCAL, MODEL_BASE)
    