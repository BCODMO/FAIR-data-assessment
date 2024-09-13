import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)  ## remove pandas future warning

# pyshack sends output to log along with the vars.  This suppresses that
import logging, sys
from pathlib import Path
logging.disable(sys.maxsize)
import os
import kglab
import re
from urllib.request import urlopen
import sys
from datetime import datetime
from reportlab.platypus import *
import argparse
from rdflib import Graph
import rdflib
import pyoxigraph

# this code doesn't use pyoxigraph, however, it would be nice to migrate to it
# In the expectation of that, this extract_value function is included but not
# yet used.  Would use it like df = df.applymap(extract_value)

# This map is necessary to get the values from the oxigraph query response objects.
def extract_value(cell):
    if isinstance(cell, (pyoxigraph.Literal, pyoxigraph.NamedNode, pyoxigraph.BlankNode)):
        return cell.value
    return cell

def read_path(path: str):
    # Regular expression to check if the path is a URL
    url_regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if re.match(url_regex, path):
        # If path is a URL, read from the URL
        with urlopen(path) as response:
            data = response.read()
    else:
        # If path is a local file, read from the file
        if os.path.isfile(path):
            with open(path, 'rb') as file:
                data = file.read()
        else:
            raise ValueError("Invalid path: Neither a valid URL nor a local file")

    return data

# This function doesn't use KGlab
def shaclRun_rdflib(data_file, shacl_file, data_format, shacl_format):
    # Load the data graph
    data_graph = rdflib.Graph()
    try:
        data_graph.parse(data_file, format=data_format)
    except Exception as e:
        print(f"Error loading data graph: {e}")
        return

    # Load the SHACL shape graph
    shacl_graph = rdflib.Graph()
    try:
        shacl_graph.parse(shacl_file, format=shacl_format)
    except Exception as e:
        print(f"Error loading SHACL graph: {e}")
        return

    # Validate the data graph against the SHACL shape graph
    try:
        conforms, results_graph, results_text = validate(data_graph, shacl_graph=shacl_graph)
    except Exception as e:
        print(f"Error during validation: {e}")
        return

    # # Print validation results
    # print(f"Validation {'succeeded' if conforms else 'failed'}")
    # print(results_text)

    # Save validation results to an NT file
    results_file = "validation_results.nt"
    try:
        results_graph.serialize(destination=results_file, format="nt", encoding="utf-8")
        print(f"Validation results saved to {results_file}")
    except Exception as e:
        print(f"Error saving validation results: {e}")

# This version uses KGlab
def shaclRun(sgurl, dgurl):
    namespaces = {
        "shacl": "http://www.w3.org/ns/shacl#",
        "schema": "https://schema.org/"
    }

    kg = kglab.KnowledgeGraph(
        name="Schema.org based datagraph",
        base_uri="https://example.org/id/",
        namespaces=namespaces,
    )

    sg = read_path(sgurl)
    dg = read_path(dgurl)

    # load the shapegraph in too, so we can get to the shacl:group resources
    kg.load_rdf_text(sg, format="ttl")

    try:
        g = Graph().parse(data=dg, format='json-ld')
        r = g.serialize(format='nt')
        kg.load_rdf_text(r)
    except Exception as e:
        print("Exception: {}\n --".format(str(e)))

        raise e

    conforms, report_graph, report_text = kg.validate(
        shacl_graph=sg,
        shacl_graph_format="ttl"
    )

    kg.load_rdf_text(data=report_graph.save_rdf_text(), format="ttl")

    return kg

def validate(sgurl, dgurl):
    kg = shaclRun(sgurl, dgurl)

    sparql = """PREFIX shacl: <http://www.w3.org/ns/shacl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>

SELECT ?id ?name ?severity ?grname (STR(?refurl) AS ?str_refurl) (STR(?refresource) AS ?str_refresrouce) ?constraint ?path ?message (STR(?focus) AS ?focusURL) ?focusType ?value
WHERE {
  ?id rdf:type shacl:ValidationResult .
  ?id shacl:focusNode ?focus .
  ?id shacl:sourceShape ?ss .
  ?focus rdf:type ?focusType .
  ?id shacl:resultMessage ?message .
  ?id shacl:resultSeverity ?severity .
  ?id shacl:sourceConstraintComponent ?constraint .
  OPTIONAL {  ?ss shacl:name ?name . }
  OPTIONAL {  
    ?ss shacl:group ?group .
    ?group rdfs:label ?grname .
    ?group schema:url ?refurl .
    ?group rdfs:isDefinedBy ?refresource .
   }
  OPTIONAL { ?id shacl:resultPath ?path . }
  OPTIONAL { ?id shacl:value ?value . }
}
    """

    df = kg.query_as_df(sparql)

    return df

def main():
    # Initialize args  parser
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--datagraph", help="datagraph to check")
    parser.add_argument("-s", "--shapegraph", help="shacl shape graph to use")
    parser.add_argument("-o", "--output", help="output name as FILE.csv or FILE.parquet")

    args = parser.parse_args()
    dgurl = args.datagraph
    sgurl = args.shapegraph
    oname = args.output

    if args.datagraph is None:
        print("Datagraph (-d) is required")
        sys.exit(2)

    if args.shapegraph is None:
        print("Shapegraph (-s) is required")
        sys.exit(2)

    if args.output is None:
        print("Output path (-o) is required")
        sys.exit(2)

    # Save output
    file_suffix = Path(oname).suffix

    if file_suffix == ".csv":
        vdf = validate(sgurl, dgurl)
        vdf.to_csv(oname)
    elif file_suffix == ".parquet":
        vdf = validate(sgurl, dgurl)
        vdf.to_parquet(oname)
    elif file_suffix == ".nt":
        kg = shaclRun(sgurl, dgurl)
        kg.save_rdf(oname, format="nt", encoding="utf-8")
    else:
        print(f"Do not know how to save {file_suffix} files.")

if __name__ == '__main__':
    main()

