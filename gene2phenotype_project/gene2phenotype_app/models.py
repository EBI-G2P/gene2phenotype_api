from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.constraints import UniqueConstraint
from django.db.models import Q

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

    class Meta:
        db_table = "locus_genotype_disease"
        unique_together = ["locus", "genotype", "disease"]

class LocusGenotypeDiseaseHistory(models.Model):
    lgd_id = models.IntegerField()
    stable_id = models.CharField(max_length=100)
    locus_id = models.IntegerField()
    genotype_id = models.IntegerField()
    disease_id = models.IntegerField()
    confidence_id = models.IntegerField()
    date_review = models.DateTimeField(null=True)
    is_reviewed = models.SmallIntegerField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "locus_genotype_disease_history"

class LGDCrossCuttingModifier(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    ccm = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_cross_cutting_modifier"
        UniqueConstraint(fields=["lgd", "ccm", "publication"], name='unique_with_publication')
        UniqueConstraint(fields=["lgd", "ccm"], condition=Q(publication=None), name='unique_without_publication')

class LGDCrossCuttingModifierHistory(models.Model):
    lgd_cccm_id = models.IntegerField()
    lgd = models.IntegerField()
    ccm = models.IntegerField()
    publication = models.IntegerField()
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_cross_cutting_modifier_history"

class LGDPhenotype(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    phenotype = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_phenotype"
        UniqueConstraint(fields=["lgd", "phenotype", "publication"], name='unique_with_publication')
        UniqueConstraint(fields=["lgd", "phenotype"], condition=Q(publication=None), name='unique_without_publication')

class LGDPhenotypeHistory(models.Model):
    lgd_phenotype_id = models.IntegerField()
    lgd = models.IntegerField()
    phenotype = models.IntegerField()
    publication = models.IntegerField()
    is_deleted = models.SmallIntegerField()
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_phenotype_history"

class LGDPhenotypeComment(models.Model):
    id = models.AutoField(primary_key=True)
    lgd_phenotype = models.ForeignKey("LGDPhenotype", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    date_created = models.DateTimeField(null=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_phenotype_comment"
        # unique_together = ["lgd_phenotype", "comment", "user"]

# Types of variants reported in the publication: missense_variant, frameshift_variant, stop_gained, etc.
# Sequence ontology terms are used to describe variant types
class LGDVariantType(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    variant_type_ot = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    inheritance = models.ForeignKey("Attrib", on_delete=models.PROTECT, null=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_variant_type"
        UniqueConstraint(fields=["lgd","variant_type_ot", "publication"], name='unique_with_publication')
        UniqueConstraint(fields=["lgd","variant_type_ot"], condition=Q(publication=None), name='unique_without_publication')

class LGDVariantTypeHistory(models.Model):
    lgd_var_type_id = models.IntegerField()
    lgd = models.IntegerField()
    variant_type_ot = models.IntegerField()
    inheritance = models.IntegerField(null=True)
    publication = models.IntegerField(null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_variant_type_history"

# Comment on NMD triggering/escaping
class LGDVariantTypeComment(models.Model):
    id = models.AutoField(primary_key=True)
    variant_type = models.ForeignKey("LGDVariantType", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)

    class Meta:
        db_table = "lgd_variant_type_comment"
        # unique_together = ["variant_type", "comment", "user"]

# GenCC level of variant consequence: altered_gene_product_level, etc.
# Sequence ontology terms are used to describe GenCC variant types
# VariantGenccConsequence: links consequences with support and publications
class LGDVariantGenccConsequence(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    variant_consequence = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    support = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT, null=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_variant_gencc_consequence"
        UniqueConstraint(fields=["lgd","variant_consequence", "support", "publication"], name='unique_with_publication')
        UniqueConstraint(fields=["lgd","variant_consequence", "support"], condition=Q(publication=None), name='unique_without_publication')

class LGDVariantGenccConsequenceHistory(models.Model):
    lgd_var_gencc_id = models.IntegerField()
    lgd = models.IntegerField()
    variant_consequence = models.IntegerField()
    support = models.IntegerField()
    panel = models.IntegerField(null=True)
    publication = models.IntegerField(null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_variant_gencc_consequence_history"

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

    class Meta:
        db_table = "lgd_molecular_mechanism"
        unique_together = ["lgd", "mechanism"]

class LGDMolecularMechanismHistory(models.Model):
    lgd_mol_mechanism_id = models.IntegerField()
    lgd = models.IntegerField()
    mechanism = models.IntegerField()
    mechanism_support = models.IntegerField()
    synopsis = models.IntegerField(null=True)
    synopsis_support = models.IntegerField(null=True)
    mechanism_description = models.TextField(null=True)
    publication = models.IntegerField(null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_molecular_mechanism_history"

class LGDComment(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)

    class Meta:
        db_table = "lgd_comment"

class LGDPublication(models.Model):
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_publication"
        unique_together = ["lgd", "publication"]

class LGDPublicationHistory(models.Model):
    lgd = models.IntegerField()
    publication = models.IntegerField()
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_publication_history"

class LGDPanel(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    relevance = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "lgd_panel"
        unique_together = ["lgd", "panel"]

class LGDPanelHistory(models.Model):
    lgd_panel_id = models.IntegerField()
    lgd_id = models.IntegerField()
    panel_id = models.IntegerField()
    publication_id = models.IntegerField()
    relevance_id = models.IntegerField()
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "lgd_panel_history"

class Locus(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    sequence = models.CharField(max_length=100, null=False) # TODO: update to FK
    start = models.IntegerField(null=False)
    end = models.IntegerField(null=False)
    strand = models.SmallIntegerField(null=False, default=1)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "locus"

class LocusHistory(models.Model):
    locus_id = models.IntegerField()
    type = models.IntegerField()
    sequence = models.CharField(max_length=100)
    start = models.IntegerField()
    end = models.IntegerField()
    strand = models.SmallIntegerField()
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "locus_history"

class LocusAttrib(models.Model):
    id = models.AutoField(primary_key=True)
    locus = models.ForeignKey("Locus", on_delete=models.PROTECT)
    attrib_type = models.ForeignKey("AttribType", on_delete=models.PROTECT)
    value = models.CharField(max_length=255, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "locus_attrib"

class LocusAttribHistory(models.Model):
    locus_attrib_id = models.IntegerField()
    locus = models.IntegerField()
    attrib_type = models.IntegerField()
    value = models.CharField(max_length=255, null=False)
    source = models.IntegerField()
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "locus_attrib_history"

class Attrib(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.ForeignKey("AttribType", on_delete=models.PROTECT)
    value = models.CharField(max_length=255, null=False)

    class Meta:
        db_table = "attrib"
        unique_together = ["type", "value"]

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

class Disease(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False)
    mim = models.IntegerField(null=True)

    class Meta:
        db_table = "disease"

class DiseaseHistory(models.Model):
    disease_id = models.IntegerField()
    name = models.CharField(max_length=255)
    mim = models.IntegerField(null=True)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "disease_history"

class DiseaseSynonym(models.Model):
    id = models.AutoField(primary_key=True)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    synonym = models.CharField(max_length=255, unique=True, null=False)
    synonym_type = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    date_created = models.DateTimeField()
    user = models.ForeignKey("User", on_delete=models.PROTECT)

    class Meta:
        db_table = "disease_synonym"

class DiseasePublication(models.Model):
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    families = models.IntegerField(null=True)
    consanguinity = models.ForeignKey("Attrib", related_name='consanguinity', on_delete=models.PROTECT, null=True)
    ethnicity = models.ForeignKey("Attrib", related_name='ethnicity', on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "disease_publication"

class DiseasePublicationHistory(models.Model):
    disease = models.IntegerField()
    publication = models.IntegerField()
    families = models.IntegerField(null=True)
    consanguinity = models.IntegerField(null=True)
    ethnicity = models.IntegerField(null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "disease_publication_history"

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

    class Meta:
        db_table = "disease_phenotype"
        UniqueConstraint(fields=["disease", "phenotype", "publication"], name='unique_with_publication')
        UniqueConstraint(fields=["disease", "phenotype"], condition=Q(publication=None), name='unique_without_publication')

class DiseasePhenotypeHistory(models.Model):
    disease = models.IntegerField()
    phenotype = models.IntegerField()
    publication = models.IntegerField()
    score = models.DecimalField(max_digits=10, decimal_places=6)
    date = models.DateTimeField(null=False)
    user_id = models.IntegerField(null=False)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "disease_phenotype_history"

class DiseasePhenotypeComment(models.Model):
    id = models.AutoField(primary_key=True)
    disease_phenotype = models.ForeignKey("DiseasePhenotype", on_delete=models.PROTECT)
    comment = models.TextField()
    date_created = models.DateField()
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "disease_phenotype_comment"
        # unique_together = ["disease_phenotype", "comment", "user"]

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

class PublicationComment(models.Model):
    id = models.AutoField(primary_key=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)

    class Meta:
        db_table = "publication_comment"

class Source(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    description = models.CharField(max_length=255, null=False)
    url = models.CharField(max_length=255, null=False)

    class Meta:
        db_table = "source"

class Panel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    description = models.CharField(max_length=255, null=True)
    is_visible = models.SmallIntegerField(null=False)

    class Meta:
        db_table = "panel"

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, null=False)
    email = models.CharField(max_length=100, unique=True, null=False)
    is_deleted = models.BooleanField(default=False)
    date_joined = models.DateField(null=True)
    is_superuser = models.SmallIntegerField(default=False)
    first_name = models.CharField(max_length=100, null=True, default=False)
    last_name = models.CharField(max_length=100, null=True, default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "user"

class UserPanel(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "user_panel"

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
