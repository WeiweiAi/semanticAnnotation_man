import xml.etree.ElementTree as ET

def getRdfFile(filename):
  
    # Parse the XML
    tree = ET.parse(filename)
    root = tree.getroot()

    # Extract and print all namespaces (optional, for inspection)
    namespaces = dict([
        node for _, node in ET.iterparse(filename, events=['start-ns'])
    ])
    print("Detected namespaces:", namespaces)

    # register the namespaces
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    # Find <rdf:RDF> element(s)
    rdf_elements = root.findall(".//rdf:RDF", namespaces)
    output_filename = filename.replace('.cellml', '_rdf.xml')
    # Write to file
    with open(output_filename, 'w', encoding='utf-8') as out_file:
        out_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        for rdf in rdf_elements:
            out_file.write(ET.tostring(rdf, encoding='unicode'))

    print(f"RDF extracted and saved to {output_filename}")