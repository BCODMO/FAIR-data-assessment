# FAIR Data Assessment

A SHACL implementation over Science-on-Schema.org data graphs for FAIR Data Principles

## GOAL

To provide a framework for determining a quality of FAIR-ness over an RDF graph describing a Dataset.

## STRATEGY

1. Link SHACL Shapes to [FAIR Implementation Profile (FIP) Ontology](https://peta-pico.github.io/FAIR-nanopubs/fip/index-en.html) Questions.
2. Provide various implementations of each question - each rising in expectation. Ex: Dataset Identifier - lvl 1 - is there an identifier; lvl2 - is the identifier globally unqiue; lvl3 - does the identifier resolve on the web; lvl4 - is the identifier a DOI;
3. Visualize the performance of the Dataset graph across each FIP Question in something like a radial graph. Each point in the radial would be a single question. If the question had 5 quality checks, but a dataset graph only passed 2, the radial axis for that question would have a value of 2 out of 5.
