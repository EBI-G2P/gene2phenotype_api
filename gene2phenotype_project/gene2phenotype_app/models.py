from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords

class LocusGenotypeDisease(models.Model):
    id = models.AutoField(primary_key=True)
    stable_id = models.CharField(max_length=100, unique=True, null=False)
    locus = models.ForeignKey("Locus", on_delete=models.PROTECT)
    genotype = models.ForeignKey("Attrib", related_name='genotype', on_delete=models.PROTECT)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    confidence = models.ForeignKey("Attrib", related_name='confidence', on_delete=models.PROTECT)
    date_review = models.DateTimeField(null=True)
    is_reviewed = models.SmallIntegerField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "locus_genotype_disease"
        unique_together = ["locus", "genotype", "disease"]
        indexes = [
            models.Index(fields=['locus']),
            models.Index(fields=['disease'])
        ]

class LGDCrossCuttingModifier(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    ccm = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_cross_cutting_modifier"
        unique_together = ["lgd", "ccm", "publication"]
        indexes = [
            models.Index(fields=['lgd', 'ccm']),
        ]

class LGDPhenotype(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    phenotype = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_phenotype"
        unique_together = ["lgd", "phenotype", "publication"]
        indexes = [
            models.Index(fields=['lgd', 'phenotype']),
        ]

class LGDPhenotypeComment(models.Model):
    id = models.AutoField(primary_key=True)
    lgd_phenotype = models.ForeignKey("LGDPhenotype", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    date_created = models.DateTimeField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_phenotype_comment"

# Types of variants reported in the publication: missense_variant, frameshift_variant, stop_gained, etc.
# Sequence ontology terms are used to describe variant types
class LGDVariantType(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    variant_type_ot = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    inheritance = models.ForeignKey("Attrib", on_delete=models.PROTECT, null=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_variant_type"
        unique_together = ["lgd","variant_type_ot", "publication"]
        indexes = [
            models.Index(fields=['lgd', 'variant_type_ot']),
        ]

# Comment on NMD triggering/escaping
class LGDVariantTypeComment(models.Model):
    id = models.AutoField(primary_key=True)
    lgd_variant_type = models.ForeignKey("LGDVariantType", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)

    class Meta:
        db_table = "lgd_variant_type_comment"

# GenCC level of variant consequence: altered_gene_product_level, etc.
# Sequence ontology terms are used to describe GenCC variant types
# VariantGenccConsequence: links consequences with support and publications
class LGDVariantGenccConsequence(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    variant_consequence = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    support = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT, null=True, default=None)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True, default=None)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_variant_gencc_consequence"
        unique_together = ["lgd", "variant_consequence", "support", "publication"]

class LGDMolecularMechanism(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    mechanism = models.ForeignKey("Attrib", related_name='mechanism', on_delete=models.PROTECT)
    mechanism_support = models.ForeignKey("Attrib", related_name='mechanism_support', on_delete=models.PROTECT)
    synopsis = models.ForeignKey("Attrib", related_name='synopsis', on_delete=models.PROTECT, null=True)
    synopsis_support = models.ForeignKey("Attrib", related_name='synopsis_support', on_delete=models.PROTECT, null=True)
    mechanism_description = models.TextField(null=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_molecular_mechanism"
        unique_together = ["lgd", "mechanism"]

class LGDComment(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)

    class Meta:
        db_table = "lgd_comment"

class LGDPublication(models.Model):
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_publication"
        unique_together = ["lgd", "publication"]

class LGDPanel(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    relevance = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_panel"
        unique_together = ["lgd", "panel"]
        indexes = [
            models.Index(fields=['panel']),
            models.Index(fields=['lgd', 'panel'])
        ]

class Meta(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=100, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)
    date_update = models.DateTimeField(null=False)
    is_public = models.SmallIntegerField(null=False, default=False)
    description = models.TextField(null=True)

    class Meta:
        db_table = "meta"

class Sequence(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False)
    reference = models.ForeignKey("Attrib", on_delete=models.PROTECT)

    class Meta:
        db_table = "sequence"

class Locus(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    sequence = models.ForeignKey("Sequence", on_delete=models.PROTECT)
    start = models.IntegerField(null=False)
    end = models.IntegerField(null=False)
    strand = models.SmallIntegerField(null=False, default=1)
    name = models.CharField(max_length=255)
    history = HistoricalRecords()

    class Meta:
        db_table = "locus"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['type'])
        ]

class LocusIdentifier(models.Model):
    id = models.AutoField(primary_key=True)
    locus = models.ForeignKey("Locus", on_delete=models.PROTECT)
    identifier = models.CharField(max_length=100, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)
    history = HistoricalRecords()

    class Meta:
        db_table = "locus_identifier"
        indexes = [
            models.Index(fields=['identifier'])
        ]

class LocusAttrib(models.Model):
    id = models.AutoField(primary_key=True)
    locus = models.ForeignKey("Locus", on_delete=models.PROTECT)
    attrib_type = models.ForeignKey("AttribType", on_delete=models.PROTECT)
    value = models.CharField(max_length=255, null=False, unique=True)
    source = models.ForeignKey("Source", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "locus_attrib"
        indexes = [
            models.Index(fields=["value"]),
            models.Index(fields=["attrib_type"])
        ]

class Attrib(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.ForeignKey("AttribType", on_delete=models.PROTECT)
    value = models.CharField(max_length=255, null=False)

    def __str__(self):
        return self.value

    class Meta:
        db_table = "attrib"
        unique_together = ["type", "value"]
        indexes = [
            models.Index(fields=['value'])
        ]

class AttribType(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=255, unique=True, null=False)
    name = models.CharField(max_length=255, null=False)
    description = models.CharField(max_length=255, null=False)

    class Meta:
        db_table = "attrib_type"

class OntologyTerm(models.Model):
    id = models.AutoField(primary_key=True)
    accession = models.CharField(max_length=255, null=False, unique=True)
    term = models.CharField(max_length=255, null=False, unique=True)
    description = models.TextField(null=True)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "ontology_term"
        indexes = [
            models.Index(fields=['accession']),
            models.Index(fields=['term'])
        ]

class Disease(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False)
    mim = models.IntegerField(null=True)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease"
        indexes = [
            models.Index(fields=['name'])
        ]

class DiseaseSynonym(models.Model):
    id = models.AutoField(primary_key=True)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    synonym = models.CharField(max_length=255, unique=True, null=False)
    synonym_type = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease_synonym"
        unique_together = ['disease', 'synonym']

class DiseasePublication(models.Model):
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    families = models.IntegerField(null=True)
    consanguinity = models.ForeignKey("Attrib", related_name='consanguinity', on_delete=models.PROTECT, null=True)
    ethnicity = models.ForeignKey("Attrib", related_name='ethnicity', on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease_publication"
        unique_together = ['disease', 'publication']

class DiseaseOntology(models.Model):
    id = models.AutoField(primary_key=True)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    ontology_term = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    mapped_by_attrib = models.ForeignKey("Attrib", on_delete=models.PROTECT)

    class Meta:
        db_table = "disease_ontology"
        unique_together = ["disease", "ontology_term"]

class DiseasePhenotype(models.Model):
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    phenotype = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    score = models.DecimalField(max_digits=10, decimal_places=6 , null=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease_phenotype"
        unique_together = ["disease", "phenotype", "publication"]

class DiseasePhenotypeComment(models.Model):
    id = models.AutoField(primary_key=True)
    disease_phenotype = models.ForeignKey("DiseasePhenotype", on_delete=models.PROTECT)
    comment = models.TextField()
    date_created = models.DateField()
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "disease_phenotype_comment"

class Publication(models.Model):
    id = models.AutoField(primary_key=True)
    pmid = models.IntegerField(null=False, unique=True)
    title = models.CharField(max_length=500, null=False)
    authors = models.CharField(max_length=255, null=True)
    source = models.CharField(max_length=255, null=True)
    doi = models.CharField(max_length=255, null=True)
    year = models.IntegerField(null=True)

    class Meta:
        db_table = "publication"
        indexes = [
            models.Index(fields=['pmid'])
        ]

class PublicationComment(models.Model):
    id = models.AutoField(primary_key=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)

    class Meta:
        db_table = "publication_comment"

class Source(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    description = models.CharField(max_length=255, null=True)
    version = models.CharField(max_length=50, null=True)
    url = models.CharField(max_length=255, null=True)

    class Meta:
        db_table = "source"

class Panel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    description = models.CharField(max_length=255, null=True)
    is_visible = models.SmallIntegerField(null=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "panel"
        indexes = [
            models.Index(fields=['name'])
        ]

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, null=False)
    email = models.CharField(max_length=100, unique=True, null=False)
    is_deleted = models.BooleanField(default=False)
    date_joined = models.DateField(null=True)
    is_superuser = models.SmallIntegerField(default=False)
    first_name = models.CharField(max_length=100, null=True, default=None)
    last_name = models.CharField(max_length=100, null=True, default=None)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "user"
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email'])
        ]

class UserPanel(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "user_panel"
        indexes = [
            models.Index(fields=['user', 'panel']),
        ]

class UniprotAnnotation(models.Model):
    id = models.AutoField(primary_key=True)
    uniprot_accession = models.CharField(max_length=100, null=False)
    gene = models.ForeignKey("Locus", on_delete=models.PROTECT)
    hgnc = models.IntegerField()
    gene_symbol = models.CharField(max_length=100, null=False)
    mim = models.CharField(max_length=100, null=True)
    protein_function = models.TextField(null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "uniprot_annotation"
        indexes = [
            models.Index(fields=['uniprot_accession']),
            models.Index(fields=['hgnc'])
        ]

class gene_stats(models.Model):
    id = models.AutoField(primary_key=True)
    gene = models.ForeignKey("Locus", on_delete=models.PROTECT)
    gene_symbol = models.CharField(max_length=100, null=False)
    hgnc = models.IntegerField()
    statistic = models.ForeignKey("Publication", on_delete=models.PROTECT)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "gene_stats"
        indexes = [
            models.Index(fields=['gene'])
        ]

### Legacy data ###
class Organ(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)

    class Meta:
        db_table = "organ"

class LGDOrgan(models.Model):
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    organ = models.ForeignKey("Organ", on_delete=models.PROTECT)

    class Meta:
        db_table = "lgd_organ"

class LGDMutationConsequenceFlag(models.Model):
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    mutation_consequence = models.ForeignKey("Attrib", related_name='mutation_consequence', on_delete=models.PROTECT)
    mutation_consequence_flag = models.ForeignKey("Attrib", related_name='mutation_consequence_flag', on_delete=models.PROTECT)

    class Meta:
        db_table = "lgd_mutation_consequence_flag"
###################
