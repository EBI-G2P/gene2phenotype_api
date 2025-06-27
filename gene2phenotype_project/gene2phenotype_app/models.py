from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractUser,BaseUserManager
from simple_history.models import HistoricalRecords
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import get_date_now

class G2PStableID(models.Model):
    """
    Represents a stable identifier for a gene-to-phenotype mapping.

    Attributes:
        id (AutoField): The primary key for the G2PStableID instance.
        stable_id (CharField): The stable identifier string, maximum length 100 characters.
        is_live (BooleanField): Indicates whether the stable identifier is currently in use.
        comment (TextField): Any useful note about the G2P ID or record associated to it.
    """
    id = models.AutoField(primary_key=True)
    stable_id = models.CharField(max_length=100, null=False, unique=True)
    is_live = models.BooleanField(default=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    comment = models.TextField(null=True, default=None)
    class Meta:
        """
            Meta:
                db_table (str): The name of the database table for this model.
                unique_together (list of tuples): Defines constraints to enforce uniqueness of combinations of fields.
                In this case, ensures the combination of id and stable_id is unique.
                indexes (list of Index): Defines database indexes for this model. 
                In this case, an index is created for the stable_id field to optimize queries.
        """
        db_table = "g2p_stableid"
        indexes = [
            models.Index(fields=['stable_id'])
        ]

class CurationData(models.Model):
    """
        Represents G2P data in the process of being curated.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    stable_id = models.ForeignKey("G2PStableID", on_delete=models.PROTECT, db_column="stable_id")
    date_created = models.DateTimeField(null=False)
    date_last_update = models.DateTimeField(null=False)
    session_name = models.CharField(max_length=100, null=False, unique=True)
    json_data = models.JSONField(null=False)
    gene_symbol = models.CharField(max_length=50, null=False, default=None)
    history = HistoricalRecords()

    class Meta:
        db_table = "curation_data"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["stable_id"]),
            models.Index(fields=["session_name"]),
            models.Index(fields=["gene_symbol"])
        ]

class LocusGenotypeDisease(models.Model):
    """
        Represents a G2P record (LGD record).
        A record is characterised by a locus, genotype (allelic requeriment) and a disease.
    """
    id = models.AutoField(primary_key=True)
    stable_id = models.ForeignKey("G2PStableID", on_delete=models.PROTECT, db_column="stable_id")
    locus = models.ForeignKey("Locus", on_delete=models.PROTECT)
    genotype = models.ForeignKey("Attrib", related_name='genotype', on_delete=models.PROTECT)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    mechanism = models.ForeignKey("CVMolecularMechanism", related_name='mechanism', on_delete=models.PROTECT, null=False)
    mechanism_support = models.ForeignKey("CVMolecularMechanism", related_name='mechanism_support', on_delete=models.PROTECT, null=False)
    confidence = models.ForeignKey("Attrib", related_name='confidence', on_delete=models.PROTECT) # confidence value
    confidence_support = models.TextField(null=True, default=None) # text summary to support the confidence value
    date_review = models.DateTimeField(null=True)
    is_reviewed = models.SmallIntegerField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "locus_genotype_disease"
        unique_together = ["locus", "genotype", "disease", "mechanism"]
        indexes = [
            models.Index(fields=['locus']),
            models.Index(fields=['disease']),
            models.Index(fields=['confidence']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['is_reviewed'])
        ]

class LGDMolecularMechanismSynopsis(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT, null=False)
    synopsis = models.ForeignKey("CVMolecularMechanism", related_name='synopsis', on_delete=models.PROTECT)
    synopsis_support = models.ForeignKey("CVMolecularMechanism", related_name='synopsis_support', on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_mechanism_synopsis"
        indexes = [
            models.Index(fields=['lgd'])
        ]

class LGDMolecularMechanismEvidence(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    evidence = models.ForeignKey("CVMolecularMechanism", related_name="evidence", on_delete=models.PROTECT, default=None)
    description = models.TextField(null=True, default=None)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_mechanism_evidence"
        unique_together = ["lgd", "evidence", "publication"]

class LGDCrossCuttingModifier(models.Model):
    """
        Represents the cross cutting modifier term associated with the G2P record.
    """
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    ccm = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_cross_cutting_modifier"
        unique_together = ["lgd", "ccm"]
        indexes = [
            models.Index(fields=['lgd', 'ccm']),
        ]

class LGDPhenotype(models.Model):
    """
        Represents the phenotype (ontology term) associated with the G2P record.
    """
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

class LGDPhenotypeSummary(models.Model):
    """
        Summary of the phenotypes reported in a publication for a G2P record.
        This is not directly linked to a phenotype.
    """
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    summary = models.TextField(null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_phenotype_summary"

class LGDVariantType(models.Model):
    """
        Represents the variant type associated with the G2P record and a publication.

        Types of variants reported in the publication: missense_variant, frameshift_variant, stop_gained, etc.
        Sequence ontology terms are used to describe variant types.
    """
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    variant_type_ot = models.ForeignKey("OntologyTerm", related_name="variant_type", on_delete=models.PROTECT)
    inherited = models.BooleanField(default=False)
    de_novo = models.BooleanField(default=False)
    unknown_inheritance = models.BooleanField(default=False)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_variant_type"
        unique_together = ["lgd","variant_type_ot", "publication"]
        indexes = [
            models.Index(fields=['lgd', 'variant_type_ot']),
            models.Index(fields=['variant_type_ot'])
        ]

class LGDVariantTypeDescription(models.Model):
    """
        Represents the HGVS description linked to the LGD record and the publication.
        The HGVS is not directly linked to the variant type.
    """
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    description = models.CharField(max_length=250, null=False)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_variant_type_description"

class LGDVariantTypeComment(models.Model):
    """
        Represents a comment linked to the lgd-variant type.
        Curators can add comments to the variant types, they can be public or private.
    """
    id = models.AutoField(primary_key=True)
    lgd_variant_type = models.ForeignKey("LGDVariantType", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_variant_type_comment"

class LGDVariantGenccConsequence(models.Model):
    """
        Links a G2P record to variant consequences with support (inferred/evidence).
        GenCC level of variant consequence: altered_gene_product_level, etc.
        Sequence ontology terms are used to describe GenCC variant types.
    """
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    variant_consequence = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    support = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "lgd_variant_gencc_consequence"
        unique_together = ["lgd", "variant_consequence", "support"]
        indexes = [
            models.Index(fields=['variant_consequence'])
        ]

class CVMolecularMechanism(models.Model):
    """
        Controlled vocabulary for molecular mechanism
    """

    # Type of vocabulary available for the mechanism
    choices_values = (
        ("mechanism", "Molecular mechanism"),
        ("mechanism_synopsis", "Mechanism synopsis"),
        ("support", "Mechanism support"),
        ("evidence", "Mechanism evidence")
    )

    # Type of vocabulary available for the evidence
    # The evidence values are a subtype of type "evidence"
    choices_evidence_types = (
        ("function", "Function"),
        ("rescue", "Rescue"),
        ("functional_alteration", "Functional alteration"),
        ("models", "Models")
    )

    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, choices=choices_values)
    # the subtype is only populated for the evidence
    subtype = models.CharField(max_length=100, choices=choices_evidence_types, null=True)
    value = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "cv_molecular_mechanism"
        unique_together = ["type", "subtype", "value"]

class LGDComment(models.Model):
    id = models.AutoField(primary_key=True)
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)
    history = HistoricalRecords()

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
    relevance = models.ForeignKey("Attrib", on_delete=models.PROTECT, null=True)
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
    """
        Meta table can be used to keep track of bulk updates.
    """
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=100, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)
    date_update = models.DateTimeField(null=False)
    is_public = models.SmallIntegerField(null=False, default=False)
    description = models.TextField(null=True)
    version = models.CharField(max_length=20, null=False)

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
    description = models.CharField(max_length=255, null=True, default=None)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "locus_identifier"
        indexes = [
            models.Index(fields=['identifier'])
        ]

class LocusAttrib(models.Model):
    id = models.AutoField(primary_key=True)
    locus = models.ForeignKey("Locus", on_delete=models.PROTECT)
    attrib_type = models.ForeignKey("AttribType", on_delete=models.PROTECT)
    value = models.CharField(max_length=255, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "locus_attrib"
        unique_together = ["locus", "value", "attrib_type"]
        indexes = [
            models.Index(fields=["value"]),
            models.Index(fields=["attrib_type"])
        ]

class Attrib(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.ForeignKey("AttribType", on_delete=models.PROTECT)
    value = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True, blank=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)

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
    is_deleted = models.SmallIntegerField(null=False, default=False)

    class Meta:
        db_table = "attrib_type"

class OntologyTerm(models.Model):
    """
        Ontology term can be of different types:
            - disease (Mondo, OMIM)
            - phenotype (HPO)
            - variant type (SO)
        Different sources can have the same term which means in this table
        the same term can be linked to different accessions (coming from different sources)
    """
    id = models.AutoField(primary_key=True)
    accession = models.CharField(max_length=255, null=False, unique=True)
    term = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)
    group_type = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    history = HistoricalRecords()

    class Meta:
        db_table = "ontology_term"
        unique_together = ["accession", "term"]
        indexes = [
            models.Index(fields=['accession']),
            models.Index(fields=['term']),
            models.Index(fields=['group_type'])
        ]

class Disease(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease"
        indexes = [
            models.Index(fields=['name'])
        ]

class DiseaseSynonym(models.Model):
    id = models.AutoField(primary_key=True)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    synonym = models.CharField(max_length=255, null=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease_synonym"
        unique_together = ['disease', 'synonym']
        indexes = [
            models.Index(fields=['synonym'])
        ]

class DiseaseOntologyTerm(models.Model):
    """
        Links the disease to ontology terms imported from external ontology sources.
        Example of ontology terms for disease are: OMIM and Mondo IDs
    """
    id = models.AutoField(primary_key=True)
    disease = models.ForeignKey("Disease", on_delete=models.PROTECT)
    ontology_term = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    mapped_by_attrib = models.ForeignKey("Attrib", on_delete=models.PROTECT)
    history = HistoricalRecords()

    class Meta:
        db_table = "disease_ontology_term"
        unique_together = ["disease", "ontology_term"]
        indexes = [
            models.Index(fields=['ontology_term'])
        ]

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

class PhenotypePublication(models.Model):
    id = models.AutoField(primary_key=True)
    phenotype = models.ForeignKey("OntologyTerm", on_delete=models.PROTECT)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT, null=True)
    pheno_count = models.IntegerField(null=True) # Probably not necessary - maybe a comment
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "phenotype_publication"
        indexes = [
            models.Index(fields=["phenotype"])
        ]
        unique_together = ["phenotype", "publication"]

class Publication(models.Model):
    id = models.AutoField(primary_key=True)
    pmid = models.IntegerField(null=False, unique=True)
    title = models.CharField(max_length=500, null=False)
    authors = models.CharField(max_length=255, null=True)
    source = models.CharField(max_length=255, null=True)
    doi = models.CharField(max_length=255, null=True)
    year = models.IntegerField(null=True)
    history = HistoricalRecords()

    class Meta:
        db_table = "publication"
        indexes = [
            models.Index(fields=['pmid'])
        ]

class PublicationFamilies(models.Model):
    id = models.AutoField(primary_key=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    families = models.IntegerField(null=False)
    consanguinity = models.ForeignKey("Attrib", related_name='consanguinity_publication', on_delete=models.PROTECT, null=True)
    affected_individuals = models.IntegerField(null=True)
    ancestries = models.CharField(max_length=500, null=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "publication_families"
        indexes = [
            models.Index(fields=["publication"])
        ]
        unique_together = ["publication", "families", "consanguinity", "affected_individuals"]

class PublicationComment(models.Model):
    id = models.AutoField(primary_key=True)
    publication = models.ForeignKey("Publication", on_delete=models.PROTECT)
    comment = models.TextField(null=False)
    is_public = models.SmallIntegerField(null=False, default=True)
    is_deleted = models.SmallIntegerField(null=False, default=False)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    date = models.DateTimeField(null=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "publication_comment"

class Source(models.Model):
    """
        External sources from where data is retrieved.
        Example: UniProt
    """
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
    description = models.CharField(max_length=255, null=False, default="before_G2P_2025") #default was added because this is the default settings for django when changing from null=True to null=False
    is_visible = models.SmallIntegerField(null=False)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "panel"
        indexes = [
            models.Index(fields=['name'])
        ]

class UserManager(BaseUserManager):
    def create_user(self, email, username, first_name, last_name, password=None, is_superuser=False, is_staff=False):

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_superuser=is_superuser,
            is_staff=is_staff,
            date_joined=get_date_now(),
        )

        user.set_password(password)
        user.save()
        return user

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, null=False)
    email = models.CharField(max_length=100, unique=True, null=False)
    is_deleted = models.BooleanField(default=False)
    date_joined = models.DateField(null=True)
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=100, null=True, default=None)
    last_name = models.CharField(max_length=100, null=True, default=None)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

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
    """
        It represents the gene product function from UniProt.
    """

    id = models.AutoField(primary_key=True)
    uniprot_accession = models.CharField(max_length=100, null=False)
    gene = models.ForeignKey("Locus", on_delete=models.PROTECT)
    hgnc = models.CharField(max_length=50, null=False) # TODO remove this field
    gene_symbol = models.CharField(max_length=100, null=False) # TODO remove this field
    mim = models.CharField(max_length=100, null=True) # TODO remove this field
    protein_function = models.TextField(null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "uniprot_annotation"
        indexes = [
            models.Index(fields=['uniprot_accession']),
            models.Index(fields=['hgnc'])
        ]

class GeneStats(models.Model):
    id = models.AutoField(primary_key=True)
    gene = models.ForeignKey("Locus", on_delete=models.PROTECT)
    gene_symbol = models.CharField(max_length=100, null=False)
    score = models.FloatField(default='0.0')
    source = models.ForeignKey("Source", on_delete=models.PROTECT)
    description_attrib  = models.ForeignKey("Attrib", default='', on_delete=models.PROTECT)

    class Meta:
        db_table = "gene_stats"
        indexes = [
            models.Index(fields=['gene']),
        ]

class GeneDisease(models.Model):
    """
        External gene-disease associations.
        Data imported from OMIM, Mondo, etc.
    """
    id = models.AutoField(primary_key=True)
    gene = models.ForeignKey("Locus", on_delete=models.PROTECT)
    disease = models.CharField(max_length=255, null=False)
    identifier = models.CharField(max_length=50, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "gene_disease"
        unique_together = ['gene', 'disease', 'source']
        indexes = [
            models.Index(fields=['gene']),
            models.Index(fields=['disease'])
        ]

class DiseaseExternal(models.Model):
    """
        Disease IDs from external sources and respective disease name.
        This data is imported in bulk from the source (ex: Mondo) and will
        be used by curators to link G2P diseases to external disease IDs.
    """
    id = models.AutoField(primary_key=True)
    disease = models.CharField(max_length=255, null=False)
    identifier = models.CharField(max_length=50, null=False)
    source = models.ForeignKey("Source", on_delete=models.PROTECT)

    class Meta:
        db_table = "disease_external"
        unique_together = ['disease', 'source']
        indexes = [
            models.Index(fields=['identifier'])
        ]

### Table to keep track of GenCC submissions ###
class GenCCSubmission(models.Model):
    """
        Store the info when the record was submitted to GenCC.
            - id: primary key
            - submission_id: genCC ID associated with the G2P record
            - old_g2p_id: internal G2P ID in the old system (only relevant for submissions with the old data)
            - g2p_stable_id: new G2P stable ID
            - date_of_submission: date when record was submitted to GenCC
            - type_of_submission: 'create' if we submitted a new G2P record to GenCC or 'update' if we updated an existing G2P record in GenCC
    """
    SUBMISSION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
    ]
    id = models.AutoField(primary_key=True)
    submission_id = models.CharField(max_length=64)
    old_g2p_id = models.IntegerField(null=True, default=False)
    g2p_stable_id = models.ForeignKey("G2PStableID", on_delete=models.PROTECT, db_column="g2p_stable_id")
    date_of_submission = models.DateField(null=False)
    type_of_submission = models.CharField(max_length=50, choices=SUBMISSION_CHOICES, default="create")

    class Meta:
        db_table = "gencc_submission"
###################


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
    """
        As some mutation consequences flags are not migrated, we keep the legacy data in this table.
    """
    lgd = models.ForeignKey("LocusGenotypeDisease", on_delete=models.PROTECT)
    mutation_consequence_flag = models.ForeignKey("Attrib", related_name='mutation_consequence_flag', on_delete=models.PROTECT)

    class Meta:
        db_table = "lgd_mutation_consequence_flag"
###################
