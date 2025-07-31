#!/usr/bin/env python3

import re
import requests


def latin2arab(match):
    latin = match.group(1)

    return (
        "type "
        + {
            "i": "1",
            "ii": "2",
            "iii": "3",
            "iv": "4",
            "v": "5",
            "vi": "6",
            "vii": "7",
            "viii": "8",
            "ix": "9",
            "xvii": "17",
            "xxi": "21",
        }[latin]
    )


def clean_string(name):
    new_disease_name = name.strip()

    new_disease_name = new_disease_name.lstrip("?")
    new_disease_name = new_disease_name.rstrip(".")
    new_disease_name = re.sub(r",\s+", " ", new_disease_name)
    new_disease_name = new_disease_name.replace("“", "").replace("”", "")
    new_disease_name = new_disease_name.replace("-", " ")
    new_disease_name = re.sub(r"\t+", " ", new_disease_name)

    new_disease_name = new_disease_name.lower()

    new_disease_name = re.sub(r"\s+and\s+", " ", new_disease_name)
    new_disease_name = re.sub(r"\s+or\s+", " ", new_disease_name)

    # remove 'biallelic' and 'autosomal'
    new_disease_name = re.sub(r"biallelic$", "", new_disease_name)
    new_disease_name = re.sub(r"autosomal$", "", new_disease_name)
    new_disease_name = re.sub(r"\(biallelic\)$", "", new_disease_name)
    new_disease_name = re.sub(r"\(autosomal\)$", "", new_disease_name)

    new_disease_name = re.sub(r"type ([xvi]+)$", latin2arab, new_disease_name)

    # remove 'type'
    if re.search(r"\s+type\s+[0-9]+[a-z]?$", new_disease_name):
        new_disease_name = re.sub(r"\s+type\s+", " ", new_disease_name)

    new_disease_name = re.sub(r"\(|\)", " ", new_disease_name)
    new_disease_name = re.sub(r"\s+", " ", new_disease_name)

    # tokenise string
    disease_tokens = sorted(new_disease_name.split())

    return " ".join(disease_tokens)


# Clean OMIM disease name
# Removes the gene and subtype from the disease name
# Example: "BLEPHAROCHEILODONTIC SYNDROME 1; BCDS1" -> "blepharocheilodontic syndrome"
def clean_omim_disease(name):
    disease_name = name.split(";")[0]
    disease_name = re.sub(
        r",*\s*(TYPE)*,*\s+([0-9]+[A-Z]{0,2}|[IVX]{0,3})$", "", disease_name
    )

    # Some disease names have the subtype in the middle
    # Remove the integers but keep the word 'syndrome'
    # Example: "ALPORT SYNDROME 2, AUTOSOMAL RECESSIVE; ATS2"
    disease_name = re.sub(r"SYNDROME\s+[0-9]+,*", "SYNDROME", disease_name)
    # After: "alport syndrome autosomal recessive"

    # If the integer is preceded by 'type' then remove both
    # Example before: "TYPE 1 DIABETES MELLITUS; T1D"
    disease_name = re.sub(r"TYPE\s+[0-9]+,*", "", disease_name)
    # After: "diabetes mellitus"

    return disease_name.lower().strip()


"""
    Get the ontology info from the disease ID

    Input:
            id: disease ID
            source: source name
    Output:
            ols response
            return None if no response or source is invalid
"""


def get_ontology(id, source):
    if source.lower() == "mondo":
        url = f"https://www.ebi.ac.uk/ols4/api/search?q={id}&ontology=mondo&exact=1"

    elif source.lower() == "omim":
        url = f"https://www.ebi.ac.uk/ols4/api/search?q={id}&ontology=cco"

    else:
        return None

    r = requests.get(url, headers={"Content-Type": "application/json"})

    if not r.ok:
        return "query failed"

    decoded = r.json()

    if (
        len(decoded["response"]["docs"]) > 0
        and "label" in decoded["response"]["docs"][0]
    ):
        name = decoded["response"]["docs"][0]
    else:
        name = None

    return name


"""
    To store the ontology ID/term we have to know its source.
    The source can be OMIM or Mondo.

    Input: disease ID
    Output: source of the disease ID (Mondo or OMIM)
            the source name is going to be used to fetch the source id from the db (case sensitive)
"""


def get_ontology_source(id):
    source = None

    if id.startswith("MONDO"):
        source = "Mondo"
    elif id.isdigit():
        source = "OMIM"

    return source


def check_synonyms_disease(disease_name: str) -> str:
    """
    Given a disease name from OMIM or Mondo returns the associated G2P disease synonym.
    The output G2P disease is represented in lower case and without 'gene-related'.

    Args:
        disease_name (str): disease name in lower case from OMIM or Mondo

    Returns:
        str: returns the synonym disease name in lower case
    """

    synonyms_list = {
        "hypopigmentation-punctate palmoplantar keratoderma syndrome": "cole disease",
        "lissencephaly 5": "cobblestone brain malformation without muscular or ocular abnormalities",
        "schuurs-hoeijmakers syndrome": "intellectual disability",
        "peeling skin syndrome 4": "exfoliative ichthyosis, autosomal recessive, ichthyosis bullosa of siemens-like",
        "tonne-kalscheuer syndrome": "intellectual disability",
        "microcephaly, growth restriction, and increased sister chromatid exchange 2": "bloom syndrome like disorder",
        "brain small vessel disease 1 with or without ocular anomalies": "porencephaly",
        "houge-janssens syndrome 1": "intellectual disability",
        "houge-janssens syndrome 2": "intellectual disability",
        "miller syndrome": "postaxial acrofacial dysostosis",
        "harel-yoon syndrome": "disorder with global developmental delay, hypotonia, optic atrophy, axonal neuropathy, and hypertrophic cardiomyopathy",
        "cortical dysplasia, complex, with other brain malformations 7": "polymicrogyria asymmetric",
        "septooptic dysplasia": "combined pituitary hormone deficiency",
        "traboulsi syndrome": "dysmorphism, lens dislocation, anterior segment abnormalities, and filtering blebs",
        "kufor-rakeb syndrome": "parkinson disease",
        "lynch syndrome 8": "colorectal cancer, hereditary nonpolyposis",
        "shashi-pena syndrome": "developmental delay, macrocephaly, and dysmorphic features",
        "raynaud-claes syndrome": "infantile epileptic encephalopathy and/or intellectual disability",
        "fg syndrome 4": "intellectual developmental disorder, with or without nystagmus",
        "skraban-deardorff syndrome": "intellectual disability, seizures, abnormal gait, and distinctive facial features",
        "alkuraya-kucinskas syndrome": "brain atrophy, dandy walker and contractures",
        "wieacker-wolff syndrome": "arthrogryposis multiplex congenita and intellectual disability",
        "peeling skin with leukonychia, acral punctate keratoses, cheilitis, and knuckle pads": "plack syndrome",
        "bone mineral density quantitative trait locus 18": "osteoporosis with fractures",
        "macs syndrome": "macrocephaly, alopecia, cutis laxa, and scoliosis tall forehead, sparse hair, skin hyperextensibility, and scoliosis",
        "acces syndrome": "congenital anomalies with or without aplasia cutis congenita and ectrodactyly and variable developmental delay",
        "seckel syndrome 8": "microcephalic primordial dwarfism with or without poikiloderma and cataracts",
        "gand syndrome": "nonspecific severe intellectual disability",
        "methylmalonic aciduria and homocystinuria, cblx type": "intellectual developmental disorder",
        "renu syndrome": "neurodevelopmental disorder with microcephaly and seizures",
        "usmani-riazuddin syndrome, autosomal recessive": "intellectual disability, biallelic",
        "ritscher-schinzel syndrome 1": "intellectual disability, congenital cardiac malformation, and Dandy-Walker malformation",
        "myoclonic epilepsy associated with ragged-red fibers": "merrf syndrome",
        "mirage syndrome": "myelodysplasia, infection, restriction of growth, adrenal hypoplasia, genital phenotypes, enteropathy (mirage)",
        "cowden syndrome 1": "lhermitte-duclos disease",
        "muscular dystrophy-dystroglycanopathy (congenital with brain and eye anomalies), type a, 7": "walker-warburg syndrome",
        "mitochondrial complex v (atp synthase) deficiency, nuclear type 4a": "failure to thrive, hyperlactatemia and hyperammonemia",
        "neurodevelopmental disorder with dysmorphic facies and skeletal and brain abnormalities": "intellectual disability",
        "chromosome 20q11-q12 deletion syndrome": "intellectual disability",
        "al kaissi syndrome": "severe growth retardation, spine malformations, and developmental delays",
        "neurodevelopmental disorder with hypotonia, speech delay, and dysmorphic facies": "intellectual disability",
        "webb-dattani syndrome": "hypopituitarism, post-natal microcephaly, visual and renal anomalies",
        "retinal dystrophy with leukodystrophy": "deficiency",
        "tumor predisposition syndrome 4": "cancer",
        "bart-pumphrey syndrome": "knuckle pads, leuconychia and sensorineural deafness",
        "ayme-gripp syndrome": "cataracts, congenital, with sensorineural deafness, down syndrome-like facial appearance, short stature, and mental retardation",
        "neurodevelopmental disorder with speech impairment and dysmorphic facies": "intellectual disability",
        "sandhoff disease": "gm2-gangliosidosis",
        "cortical dysplasia, complex, with other brain malformations 14a (bilateral frontoparietal)": "polymicrogyria",
        "intellectual developmental disorder with microcephaly and with or without ocular malformations or hypogonadotropic hypogonadism": "neurodevelopmental disorder",
        "white-sutton syndrome": "intellectual disability",
        "usmani-riazuddin syndrome, autosomal dominant": "intellectual disability and epilepsy, monoallelic",
        "combined oxidative phosphorylation deficiency 10": "infantile hypertrophic cardiomyopathy and lactic acidosis",
        "immunodeficiency 129": "epidermodysplasia verruciformis, susceptibility to",
        "coffin-siris syndrome 12": "developmental disorder",
        "hamamy syndrome": "hypertelorism, severe, with midface prominence, myopia, intellectual developmental disorder, and bone fragility",
        "neurodevelopmental disorder with hypotonia and impaired expressive language and with or without seizures": "autism, intellectual disability, basal ganglia dysfunction and epilepsy",
        "intrauterine growth retardation, metaphyseal dysplasia, adrenal hypoplasia congenita, and genital anomalies": "image syndrome",
        "bardet-biedl syndrome 22": "ciliopathy",
        "vici syndrome": "immunodeficiency, cardiomyopathy, cataract, hypopigmentation, and absent corpus callosum",
        "immunodysregulation, polyendocrinopathy, and enteropathy, x-linked": "ipex syndrome",
        "kleefstra syndrome 2": "intellectual disability",
        "townes-brocks syndrome 2": "multiple malformations of neural tube, ear, genitourinary and gastrointestinal systems",
        "muscular dystrophy-dystroglycanopathy (congenital with brain and eye anomalies), type a, 8": "walker warberg spectrum disorder",
        "heyn-sproul-jackson syndrome": "microcephalic primordial dwarfism",
        "hsd10 mitochondrial disease": "2-methyl-3-hydroxybutyryl-coa dehydrogenase deficiency",
        "chanarin-dorfman syndrome": "ichthyotic neutral lipid storage disease",
        "carpenter syndrome 1": "acrocephalopolysyndactyly",
        "chops syndrome": "cornelia de lange-like syndrome",
        "salt and pepper developmental regression syndrome": "amish infantile epilepsy syndrome",
        "metachromatic leukodystrophy": "arylsulfatase a deficiency",
        "pseudohypoparathyroidism, type ia": "albright hereditary osteodystrophy",
    }

    try:
        g2p_disease_name = synonyms_list[disease_name]
    except:
        g2p_disease_name = None

    return g2p_disease_name
