from rest_framework import serializers
from django.db import connection, IntegrityError
from django.db.models import Prefetch
from django.conf import settings
from typing import Any, Optional
from datetime import date
import re

from ..models import (
    Panel,
    Attrib,
    LGDPanel,
    LocusGenotypeDisease,
    LGDVariantGenccConsequence,
    LGDCrossCuttingModifier,
    LGDPublication,
    LGDPhenotype,
    LGDVariantType,
    Locus,
    LGDComment,
    LGDVariantTypeComment,
    User,
    LGDMolecularMechanismEvidence,
    CVMolecularMechanism,
    OntologyTerm,
    Publication,
    LGDPhenotypeSummary,
    LGDVariantTypeDescription,
    LGDMolecularMechanismSynopsis,
)

from .publication import LGDPublicationSerializer
from .locus import LocusSerializer
from .disease import DiseaseSerializer
from .panel import LGDPanelSerializer

from ..utils import get_date_now, ConfidenceCustomMail
from ..utils import validate_mechanism_synopsis, validate_confidence_publications


class LocusGenotypeDiseaseSerializer(serializers.ModelSerializer):
    """
    Serializer for the LocusGenotypeDisease model.
    LocusGenotypeDisease represents a unique Locus-Genotype-Mechanism-Disease-Evidence (LGMDE) record.
    """

    locus = serializers.SerializerMethodField()  # part of the unique entry
    stable_id = serializers.CharField(
        source="stable_id.stable_id", read_only=True
    )  # CharField and the source is the stable_id column in the stable_id table
    genotype = serializers.CharField(
        source="genotype.value", read_only=True
    )  # part of the unique entry
    variant_consequence = serializers.SerializerMethodField(allow_null=True)
    molecular_mechanism = serializers.SerializerMethodField(allow_null=True)
    disease = serializers.SerializerMethodField()  # part of the unique entry
    confidence = serializers.CharField(source="confidence.value")
    publications = serializers.SerializerMethodField()
    panels = serializers.SerializerMethodField()
    cross_cutting_modifier = serializers.SerializerMethodField(allow_null=True)
    variant_type = serializers.SerializerMethodField(allow_null=True)
    variant_description = serializers.SerializerMethodField(allow_null=True)
    phenotypes = serializers.SerializerMethodField(allow_null=True)
    phenotype_summary = serializers.SerializerMethodField(allow_null=True)
    last_updated = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField(allow_null=True)
    is_reviewed = serializers.BooleanField(
        required=False
    )  # It is the same as SmallInteger 0/1

    def get_locus(self, id: int) -> dict[str, Any]:
        """
        Gene associated with the LGMDE record
        """
        locus = LocusSerializer(id.locus).data
        return locus

    def get_disease(self, id: int) -> dict[str, Any]:
        """
        Disease associated with the LGMDE record
        """
        disease = DiseaseSerializer(id.disease).data
        return disease

    def get_last_updated(self, obj) -> Optional[str]:
        """
        Date last time the LGMDE record was updated by a curator
        """
        if obj.date_review is not None:
            return obj.date_review.strftime("%Y-%m-%d")
        else:
            return None

    def get_variant_consequence(self, id: int) -> list[dict[str, Any]]:
        """
        Variant consequences linked to the LGMDE record.
        This is the GenCC level of variant consequence: altered_gene_product_level, etc.
        """
        queryset = LGDVariantGenccConsequence.objects.filter(lgd_id=id, is_deleted=0)
        return LGDVariantGenCCConsequenceSerializer(queryset, many=True).data

    def get_molecular_mechanism(self, id: int) -> dict[str, Any]:
        """
        Molecular mechanism associated with the LGMDE record.
        If available, also returns the evidence.
        """
        user = self.context.get("user")
        try:
            User.objects.get(email=user)
            authenticated_user = 1
        except User.DoesNotExist:
            authenticated_user = 0

        mechanism = id.mechanism.value
        mechanism_support = id.mechanism_support.value
        mechanism_synopsis = []
        mechanism_evidence = {}

        queryset_synopsis = LGDMolecularMechanismSynopsis.objects.filter(
            lgd_id=id, is_deleted=0
        ).prefetch_related()
        queryset_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd_id=id, is_deleted=0
        ).prefetch_related()

        for synopsis_data in queryset_synopsis:
            mechanism_synopsis.append(
                {
                    "synopsis": synopsis_data.synopsis.value,
                    "support": synopsis_data.synopsis_support.value,
                }
            )

        for evidence_data in queryset_evidence:
            pmid = evidence_data.publication.pmid
            evidence_type = evidence_data.evidence.subtype.replace("_", " ").title()
            evidence_value = evidence_data.evidence.value.title()

            if pmid not in mechanism_evidence:
                mechanism_evidence[pmid] = {
                    "functional_studies": {evidence_type: [evidence_value]},
                    "descriptions": [],
                }
                # If description is defined and the user is authenticated,
                # overwrite the description in the output
                if evidence_data.description and authenticated_user == 1:
                    mechanism_evidence[pmid]["descriptions"] = [
                        evidence_data.description
                    ]
            else:
                existing_evidence = mechanism_evidence[pmid]
                # Update functional studies list
                if evidence_type in existing_evidence["functional_studies"]:
                    mechanism_evidence[pmid]["functional_studies"][
                        evidence_type
                    ].append(evidence_value)
                else:
                    mechanism_evidence[pmid]["functional_studies"][evidence_type] = [
                        evidence_value
                    ]
                # Update description
                if (
                    evidence_data.description
                    and authenticated_user == 1
                    and evidence_data.description
                    not in mechanism_evidence[pmid]["descriptions"]
                ):
                    mechanism_evidence[pmid]["descriptions"].append(
                        evidence_data.description
                    )

        mechanism_result = {
            "mechanism": mechanism,
            "mechanism_support": mechanism_support,
            "synopsis": mechanism_synopsis,
            "evidence": mechanism_evidence,
        }

        return mechanism_result

    def get_cross_cutting_modifier(self, id: int) -> list[dict[str, str]]:
        """
        Cross cutting modifier terms associated with the LGMDE record.
        """
        queryset = LGDCrossCuttingModifier.objects.filter(lgd_id=id, is_deleted=0)
        return LGDCrossCuttingModifierSerializer(queryset, many=True).data

    def get_publications(self, id: int) -> list[dict[str, dict[str, Any]]]:
        """
        Publications associated with the LGMDE record.
        """
        queryset = LGDPublication.objects.filter(lgd_id=id, is_deleted=0)
        # It is necessary to send the user to return public/private comments
        return LGDPublicationSerializer(
            queryset, context={"user": self.context.get("user")}, many=True
        ).data

    def get_phenotypes(self, id: int) -> list[dict[str, Any]]:
        """
        Phenotypes associated with the LGMDE record.
        The response includes the list of publications associated with the phenotype.
        """
        queryset = LGDPhenotype.objects.filter(
            lgd_id=id, is_deleted=0
        ).prefetch_related()
        data = {}

        for lgd_phenotype in queryset:
            accession = lgd_phenotype.phenotype.accession
            publication = lgd_phenotype.publication

            if accession in data and publication:
                data[accession]["publications"].append(publication.pmid)
            else:
                publication_list = []
                if publication:
                    publication_list = [publication.pmid]

                data[accession] = {
                    "term": lgd_phenotype.phenotype.term,
                    "accession": accession,
                    "publications": publication_list,
                }

        return data.values()

    def get_phenotype_summary(self, id: int) -> list[dict[str, Any]]:
        """
        A summary about the phenotypes associated with the LGMDE record.
        The response includes the publication associated with the summary.
        """
        # The LGD record is supposed to have one summary
        # but one summary can be linked to several publications
        queryset = LGDPhenotypeSummary.objects.filter(
            lgd_id=id, is_deleted=0
        ).prefetch_related()
        data = {}

        for summary_obj in queryset:
            summary_text = summary_obj.summary

            data[summary_text] = {
                "summary": summary_text,
                "publication": summary_obj.publication.pmid,
            }

        return data.values()

    def get_variant_type(self, id: int) -> list[dict[str, Any]]:
        """
        Variant types associated with the LGMDE record.
        The variant type can be linked to several publications therefore response
        includes the list of publications associated with the variant type.
        """
        # Check if user is authenticated
        user = self.context.get("user")
        try:
            User.objects.get(email=user)
            authenticated_user = 1
        except User.DoesNotExist:
            authenticated_user = 0

        if authenticated_user == 1:
            # Authenticated users have access to comments
            queryset = LGDVariantType.objects.filter(
                lgd_id=id, is_deleted=0
            ).prefetch_related(
                Prefetch(
                    "lgdvarianttypecomment_set",
                    queryset=LGDVariantTypeComment.objects.filter(
                        is_deleted=0
                    ),  # skip deleted comments
                    to_attr="current_comments",  # prefetched comments are saved under 'current_comments'
                )
            )
        else:
            queryset = LGDVariantType.objects.filter(lgd_id=id, is_deleted=0)

        data = {}

        list_of_comments = {}
        for lgd_variant in queryset:
            # Get the variant type term (ex:frameshift_variant)
            accession = lgd_variant.variant_type_ot.accession

            # Prepare the list of comments
            comments = getattr(
                lgd_variant, "current_comments", []
            )  # Get the prefetched comments

            for comment_obj in comments:
                comment_text = comment_obj.comment
                # Format date
                date = None
                if comment_obj.date is not None:
                    date = comment_obj.date.strftime("%Y-%m-%d")

                if accession not in list_of_comments:
                    list_of_comments[accession] = [{"text": comment_text, "date": date}]
                elif not any(
                    comment["text"] == comment_text
                    for comment in list_of_comments[accession]
                ):
                    list_of_comments[accession].append(
                        {"text": comment_text, "date": date}
                    )

            if accession in data and lgd_variant.publication:
                variant_type_comments = []
                if accession in list_of_comments:
                    variant_type_comments = list_of_comments[accession]

                # Add pmid to list of publications
                data[accession]["publications"].append(lgd_variant.publication.pmid)
                data[accession]["comments"] = variant_type_comments
                # Check the variant inheritance - we group this data for each publication
                if lgd_variant.inherited is True:
                    data[accession]["inherited"] = lgd_variant.inherited
                if lgd_variant.de_novo is True:
                    data[accession]["de_novo"] = lgd_variant.de_novo
                if lgd_variant.unknown_inheritance is True:
                    data[accession]["unknown_inheritance"] = (
                        lgd_variant.unknown_inheritance
                    )
            else:
                publication_list = []
                if lgd_variant.publication:
                    publication_list = [lgd_variant.publication.pmid]

                variant_type_comments = []
                if accession in list_of_comments:
                    variant_type_comments = list_of_comments[accession]

                data[accession] = {
                    "term": lgd_variant.variant_type_ot.term,
                    "accession": accession,
                    "inherited": lgd_variant.inherited,
                    "de_novo": lgd_variant.de_novo,
                    "unknown_inheritance": lgd_variant.unknown_inheritance,
                    "publications": publication_list,
                    "comments": variant_type_comments,
                }

        return data.values()

    def get_variant_description(self, id: int) -> list[dict[str, Any]]:
        """
        Variant HGVS description linked to the LGMDE record and publication(s).
        The response includes a list of publications associated with the HGVS description.
        """
        queryset = LGDVariantTypeDescription.objects.filter(
            lgd_id=id, is_deleted=0
        ).prefetch_related()
        data = {}

        for lgd_variant in queryset:
            if lgd_variant.description in data and lgd_variant.publication:
                data[lgd_variant.description]["publications"].append(
                    lgd_variant.publication.pmid
                )
            else:
                publication_list = []
                if lgd_variant.publication:
                    publication_list = [lgd_variant.publication.pmid]
                data[lgd_variant.description] = {
                    "description": lgd_variant.description,
                    "publications": publication_list,
                }

        return data.values()

    def get_panels(self, id: int) -> list[dict[str, str]]:
        """
        Panel(s) associated with the LGMDE record.
        """
        # Check if user is authenticated
        user = self.context.get("user")
        try:
            User.objects.get(email=user)
            authenticated_user = 1
        except User.DoesNotExist:
            authenticated_user = 0

        # If user is autenticated return all panels
        # otherwise return only the visible panels
        if authenticated_user:
            queryset = LGDPanel.objects.filter(lgd_id=id, is_deleted=0)
        else:
            queryset = LGDPanel.objects.filter(
                lgd_id=id, is_deleted=0, panel__is_visible=1
            )

        return LGDPanelSerializer(queryset, many=True).data

    def get_comments(self, id: int) -> list[dict[str, Any]]:
        """
        Comments associated with the LGMDE record.
        Comments can be public or private. Private comments can only be
        seen by curators.
        """
        # Check if user is authenticated
        user = self.context.get("user")
        try:
            User.objects.get(email=user)
            authenticated_user = 1
        except User.DoesNotExist:
            authenticated_user = 0

        # If user is authenticated return all comments
        # otherwise return only the public comments
        if authenticated_user == 1:
            lgd_comments = LGDComment.objects.filter(
                lgd_id=id, is_deleted=0
            ).prefetch_related()
        else:
            lgd_comments = LGDComment.objects.filter(
                lgd_id=id, is_deleted=0, is_public=1
            ).prefetch_related()

        data = []
        for comment in lgd_comments:
            # Format the date
            date = None
            if comment.date is not None:
                date = comment.date.strftime("%Y-%m-%d")

            text = {
                "text": comment.comment,
                "date": date,
                "is_public": comment.is_public,
            }

            # authenticated users can have access to the user name
            if authenticated_user == 1:
                text["user"] = f"{comment.user.first_name} {comment.user.last_name}"

            data.append(text)

        return data

    def get_date_created(self, id) -> Optional[date]:
        """
        Date the LGMDE record was created.
        Dependency: this method depends on the history table.
        Note: entries that were migrated from the old db don't have the date when they were created.
        """
        date = None
        lgd_obj = self.instance
        insertion_history_type = "+"
        history_records = (
            lgd_obj.history.all()
            .order_by("history_date")
            .filter(history_type=insertion_history_type)
        )

        if history_records:
            date = history_records.first().history_date.date()

        return date

    def check_user_permission(self, lgd_obj, user_panels):
        """
        Check if user has permission to update this G2P record.

        Args:
                (lgd obj) id: locus genotype disease object
                (list) user_panels: list of panel names user can edit

        Return:
                True: if user has permission
                False: if user has no permission
        """
        lgd_panels = [panel.get("name") for panel in self.get_panels(lgd_obj.id)]
        has_common = any(item in list(lgd_panels) for item in user_panels)

        return has_common

    def create(self, data, disease_obj, publications_list):
        """
        Method to create a G2P record (LGD record).
        A record is always linked to one or more panels and publications.

        Mandatory data:
                        - locus
                        - G2P stable_id
                        - disease
                        - genotype (allelic requeriment)
                        - mechanism (TODO)
                        - panel(s)
                        - confidence
                        - publications
        """
        locus_name = data.get("locus")  # Usually this is the gene symbol
        stable_id_obj = data.get("stable_id")  # stable id obj
        genotype = data.get("allelic_requirement")  # allelic requirement
        panels = data.get("panels")  # Array of panel names
        confidence = data.get("confidence")  # confidence level
        mechanism_obj = data.get("mechanism")
        mechanism_support_obj = data.get("mechanism_support")
        if not panels or not publications_list:
            raise serializers.ValidationError(
                {
                    "message": f"Missing data to create the G2P record {stable_id_obj.stable_id}"
                }
            )

        # Check if record (LGD) is already inserted
        try:
            lgd_obj = LocusGenotypeDisease.objects.get(stable_id=stable_id_obj)
            return lgd_obj

        except LocusGenotypeDisease.DoesNotExist:
            # Get locus object
            try:
                locus_obj = Locus.objects.get(name=locus_name)
            except Locus.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid locus {locus_name}"}
                )

            # Get genotype
            try:
                genotype_obj = Attrib.objects.get(value=genotype, type__code="genotype")
            except Attrib.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid genotype value {genotype}"}
                )

            # Get confidence
            try:
                confidence_obj = Attrib.objects.get(
                    value=confidence, type__code="confidence_category"
                )
            except Attrib.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid confidence value {confidence}"}
                )

            # a check that for if the monoallelic record exists
            check = self.check_monoallelic_exists(
                genotype_obj, mechanism_obj, locus_obj, disease_obj
            )

            # Insert new G2P record (LGD)
            lgd_obj = LocusGenotypeDisease.objects.create(
                locus=locus_obj,
                stable_id=stable_id_obj,
                genotype=genotype_obj,
                disease=disease_obj,
                mechanism=mechanism_obj,
                mechanism_support=mechanism_support_obj,
                confidence=confidence_obj,
                is_reviewed=True,
                is_deleted=0,
                date_review=get_date_now(),
            )

            # Insert panels
            for panel in panels:
                try:
                    # Get name from description
                    panel_obj = Panel.objects.get(description=panel)
                except Panel.DoesNotExist:
                    raise serializers.ValidationError(
                        {"message": f"Invalid panel {panel}"}
                    )
                else:
                    data_panel = {"name": panel_obj.name}

                    # The LGDPanelSerializer fetches the object LGD from its context
                    lgd_panel_serializer = LGDPanelSerializer(
                        data=data_panel, context={"lgd": lgd_obj}
                    )

                    # Validate the input data
                    if lgd_panel_serializer.is_valid(raise_exception=True):
                        # Save the lgd-panel data, which will call the create method
                        lgd_panel_serializer.save()

            # Insert LGD-publications
            # The publication should be already stored in the db but
            # if the publication (PMID) is not found, it will create the Publication obj
            # Example: publications_list = [{ "pmid": 1234,
            #                                 "comment": {"comment": "comment text", "is_public": 1},
            #                                 "number_of_families": 5,
            #                                 "consanguinity": "",
            #                                 "ancestry": "",
            #                                 "affected_individuals": 5
            #                              }]
            # TODO: update to accept the publication objs to avoid creating the serializer here too
            for publication_data in publications_list:
                # PublicationSerializer is instantiated with the publication data and context
                lgd_publication_serializer = LGDPublicationSerializer(
                    # the data argument accepts all the publication data (pmid, families, comment)
                    # pass the user info and the lgd obj as context
                    data={"publication": publication_data},
                    context={"lgd": lgd_obj, "user": self.context.get("user")},
                )

                # Validate the publication data
                if lgd_publication_serializer.is_valid(raise_exception=True):
                    # Save the lgd-publication data which will call the create method
                    lgd_publication_serializer.save()

        return lgd_obj, check

    def check_monoallelic_exists(
        self,
        genotype_obj: object,
        mechanism_obj: object,
        locus_obj: object,
        disease_obj: object,
    ) -> bool:
        """
        Checks if the about to be created biallelic related genotype has a monoallelic related genotype with the same disease name and mechanism
        Args:
            genotype_obj (object): genotype object
            mechanism_obj (object): mechanism object
            locus_obj (object) : locus object
            disease_obj (object): disease object

        Returns:
            bool: True if it exists False if it does not
        """
        if (
            "biallelic" in genotype_obj.value
            and mechanism_obj.value == "loss of function"
        ):
            # fetch all the existing monoallelic existing obj using a django ORM query
            # such as monoallelic_autosomal etc
            monoallelic_obj = Attrib.objects.filter(value__icontains="monoallelic")
            for monoallelic in monoallelic_obj:
                if LocusGenotypeDisease.objects.filter(
                    locus=locus_obj,
                    disease=disease_obj,
                    mechanism=mechanism_obj,
                    genotype=monoallelic,
                ).exists():
                    return True

        return False

    def update(self, instance, validated_data):
        """
        Method to update the record confidence.
        """
        # validated_data example:
        # { "confidence": "definitive" }
        validated_confidence = validated_data.get("confidence", None)
        request = self.context.get("request")
        user = self.context.get("user")

        if (
            validated_confidence is not None
            and isinstance(validated_confidence, dict)
            and "value" in validated_confidence
        ):
            confidence = validated_confidence["value"]
        else:
            raise serializers.ValidationError({"error": f"Empty confidence value"})

        # Get confidence
        try:
            confidence_obj = Attrib.objects.get(
                value=confidence, type__code="confidence_category"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError(
                {"error": f"Invalid confidence value {confidence}"}
            )

        # Check new confidence is not the same as current value
        if instance.confidence == confidence_obj:
            raise serializers.ValidationError(
                {
                    "error": f"G2P record '{instance.stable_id.stable_id}' already has confidence value {confidence}"
                }
            )

        # Check if the confidence value can be updated
        queryset_lgd_publications = LGDPublication.objects.filter(
            lgd=instance, is_deleted=0
        )
        if not validate_confidence_publications(confidence, len(queryset_lgd_publications)):
            raise serializers.ValidationError(
                {
                    "error": f"Confidence '{confidence}' requires more than one publication as evidence"
                }
            )

        # Update confidence
        old_confidence = instance.confidence
        instance.confidence = confidence_obj

        # Update the 'date_review'
        instance.date_review = get_date_now()

        # Save all updates
        instance.save()
        user_obj = User.objects.get(email=user)
        if settings.SEND_MAILS is True:
            ConfidenceCustomMail(
                instance, old_confidence, user_obj, request
            ).send_confidence_update_email()

        return instance

    def update_mechanism(self, lgd_instance, validated_data):
        """
        Method to update the molecular mechanism of the LGD record.
        It only allows to update the mechanism value if current value is 'undetermined'.

        If evidence is provided, the code expects the 'evidence_types' to be populated
        otherwise the evidence data is not stored.

        Example:    "molecular_mechanism": {
                        "name": "gain of function",
                        "support": "evidence"
                    },
                    "mechanism_synopsis": [{
                        "name": "",
                        "support": ""
                    }],
                    "mechanism_evidence": [{'pmid': '25099252', 'description': 'text', 'evidence_types':
                        [{'primary_type': 'Rescue', 'secondary_type': ['Human', 'Patient Cells']}]}]

        """
        molecular_mechanism = validated_data.get(
            "molecular_mechanism", None
        )  # only updates mechanism if current value is 'undetermined'
        mechanism_synopsis_list = validated_data.get(
            "mechanism_synopsis", []
        )  # mechanism synopsis is optional
        mechanism_evidence = validated_data.get(
            "mechanism_evidence", None
        )  # molecular mechanism evidence is optional

        cv_mechanism_obj = None
        cv_support_obj = None

        # Get the mechanism name
        # "name" = "" means the mechanism value does not need to be updated
        if (
            molecular_mechanism
            and "name" in molecular_mechanism
            and molecular_mechanism["name"] != ""
        ):
            molecular_mechanism_value = molecular_mechanism[
                "name"
            ]  # the mechanism value

            try:
                cv_mechanism_obj = CVMolecularMechanism.objects.get(
                    value=molecular_mechanism_value, type="mechanism"
                )
            except CVMolecularMechanism.DoesNotExist:
                raise serializers.ValidationError(
                    {"error": f"Invalid mechanism value '{molecular_mechanism_value}'"}
                )

        # Get the mechanism support
        # "support" = "" means the mechanism support does not need to be updated
        if (
            molecular_mechanism
            and "support" in molecular_mechanism
            and molecular_mechanism["support"] != ""
        ):
            molecular_mechanism_support = molecular_mechanism[
                "support"
            ]  # the mechanism support (inferred/evidence)

            try:
                cv_support_obj = CVMolecularMechanism.objects.get(
                    value=molecular_mechanism_support, type="support"
                )
            except CVMolecularMechanism.DoesNotExist:
                raise serializers.ValidationError(
                    {
                        "error": f"Invalid mechanism support '{molecular_mechanism_support}'"
                    }
                )

        # Update LGD instance with new mechanism value only if mechanism value is "undetermined"
        if cv_mechanism_obj and lgd_instance.mechanism.value == "undetermined":
            lgd_instance.mechanism = cv_mechanism_obj

        # Update the mechanism support
        if cv_support_obj:
            lgd_instance.mechanism_support = cv_support_obj

        lgd_instance.date_review = get_date_now()
        lgd_instance.save()

        # The mechanism synopsis is optional
        for mechanism_synopsis in mechanism_synopsis_list:
            if mechanism_synopsis and mechanism_synopsis["name"] != "":
                mechanism_synopsis_value = mechanism_synopsis["name"]
                mechanism_synopsis_support = mechanism_synopsis["support"]

                cv_synopsis_obj = None
                cv_synopsis_support_obj = None

                try:
                    cv_synopsis_obj = CVMolecularMechanism.objects.get(
                        value=mechanism_synopsis_value, type="mechanism_synopsis"
                    )
                except CVMolecularMechanism.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "error": f"Invalid mechanism synopsis value '{mechanism_synopsis_value}'"
                        }
                    )

                try:
                    cv_synopsis_support_obj = CVMolecularMechanism.objects.get(
                        value=mechanism_synopsis_support, type="support"
                    )
                except CVMolecularMechanism.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "error": f"Invalid mechanism synopsis support '{mechanism_synopsis_support}'"
                        }
                    )

                # Validate synopsis
                mechanism_value = lgd_instance.mechanism.value
                if not validate_mechanism_synopsis(
                    mechanism_value, mechanism_synopsis_value
                ):
                    raise serializers.ValidationError(
                        {
                            "error": f"The categorisation '{mechanism_synopsis_value}' is not compatible with the mechanism '{mechanism_value}'. Please choose a categorisation relevant to the selected mechanism."
                        }
                    )

                # Check if synopsis already exists
                try:
                    mechanism_syn_obj = LGDMolecularMechanismSynopsis.objects.get(
                        lgd=lgd_instance, synopsis=cv_synopsis_obj
                    )
                except LGDMolecularMechanismSynopsis.DoesNotExist:
                    # Create mechanism synopsis
                    mechanism_syn_obj = LGDMolecularMechanismSynopsis.objects.create(
                        lgd=lgd_instance,
                        synopsis=cv_synopsis_obj,
                        synopsis_support=cv_synopsis_support_obj,
                        is_deleted=0,
                    )
                else:
                    if mechanism_syn_obj.is_deleted == 1:
                        mechanism_syn_obj.is_deleted = 0
                        mechanism_syn_obj.save()
                    if (
                        mechanism_syn_obj.synopsis_support.value
                        != mechanism_synopsis_support
                    ):
                        mechanism_syn_obj.synopsis_support = cv_synopsis_support_obj
                        mechanism_syn_obj.save()

        # Get evidence - the mechanism evidence was validated in the view 'LGDUpdateMechanism'
        # Example: {'pmid': '25099252', 'description': 'text', 'evidence_types':
        #          [{'primary_type': 'Rescue', 'secondary_type': ['Human', 'Patient Cells']}]}
        if mechanism_evidence:
            self.update_mechanism_evidence(lgd_instance, mechanism_evidence)

        return lgd_instance

    def update_mechanism_evidence(self, lgd_obj, validated_data):
        """
        Method to only update the evidence of the LGD molecular mechanism.

        'validated_data' example:
            "mechanism_evidence": [{
                                    "pmid": "1234",
                                    "description": "This is new evidence for the existing mechanism evidence.",
                                    "evidence_types": [ { "primary_type": "Function",
                                                          "secondary_type": [ "Biochemical" ]}
                                    ]}]
        """

        for evidence in validated_data:
            pmid = evidence["pmid"]

            # Check if the PMID exists in G2P
            # When updating the mechanism the supporting pmid used as evidence
            # have to already be linked to the LGD record
            try:
                publication_obj = Publication.objects.get(pmid=pmid)
            except Publication.DoesNotExist:
                # TODO: improve in future to insert new pmids + link them to the record
                raise serializers.ValidationError(
                    {"message": f"pmid '{pmid}' not found in G2P"}
                )

            if evidence["description"] != "":
                description = evidence["description"]
            else:
                description = None

            evidence_types = evidence["evidence_types"]
            for evidence_type in evidence_types:
                # primary_type is the evidence subtype ('rescue')
                primary_type = evidence_type.get("primary_type", None)
                if not primary_type:
                    raise serializers.ValidationError(
                        {"message": f"Empty evidence subtype"}
                    )
                primary_type = primary_type.replace(" ", "_").lower()
                # secondary_type is the evidence value ('human')
                secondary_type = evidence_type["secondary_type"]
                for m_type in secondary_type:
                    try:
                        cv_evidence_obj = CVMolecularMechanism.objects.get(
                            value=m_type.lower(), type="evidence", subtype=primary_type
                        )
                    except CVMolecularMechanism.DoesNotExist:
                        raise serializers.ValidationError(
                            {"message": f"Invalid mechanism evidence '{m_type}'"}
                        )

                    # Insert evidence
                    try:
                        mechanism_evidence_obj = (
                            LGDMolecularMechanismEvidence.objects.get(
                                lgd=lgd_obj,
                                publication=publication_obj,
                                evidence=cv_evidence_obj,
                            )
                        )
                    except LGDMolecularMechanismEvidence.DoesNotExist:
                        mechanism_evidence_obj = (
                            LGDMolecularMechanismEvidence.objects.create(
                                lgd=lgd_obj,
                                description=description,
                                publication=publication_obj,
                                evidence=cv_evidence_obj,
                                is_deleted=0,
                            )
                        )
                    else:
                        if mechanism_evidence_obj.is_deleted == 1:
                            mechanism_evidence_obj.is_deleted = 0
                            mechanism_evidence_obj.save()

        # Update LGD date_review
        lgd_obj.date_review = get_date_now()
        lgd_obj.save()

    class Meta:
        model = LocusGenotypeDisease
        exclude = [
            "id",
            "is_deleted",
            "date_review",
            "mechanism",
            "mechanism_support",
            "confidence_support",
        ]


class LGDCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDComment model.
    """

    def create(self, data):
        """
        Method to add a comment to a G2P entry.
        """

        comment = data.get("comment")
        is_public = data.get("is_public")
        lgd = self.context["lgd"]
        user = self.context["user"]

        # Remove newlines from comment
        comment = re.sub(r"\n", " ", comment)

        # Check if this comment is already linked to the G2P entry
        lgd_comments = LGDComment.objects.filter(
            lgd_id=lgd, is_deleted=0, comment=comment
        )

        if lgd_comments:
            raise serializers.ValidationError(
                {
                    "message": f"Comment is already associated with {lgd.stable_id.stable_id}"
                }
            )

        else:
            try:
                lgd_comment_obj = LGDComment.objects.create(
                    lgd=lgd,
                    comment=comment,
                    is_public=is_public,
                    is_deleted=0,
                    user=user,
                    date=get_date_now(),
                )
            except IntegrityError as e:
                raise IntegrityError(f"{e}")

        return lgd_comment_obj

    class Meta:
        model = LGDComment
        exclude = ["id", "is_deleted", "lgd", "date", "user"]


class LGDCommentListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of comments.
    Called by: view LGDEditComment()
    """

    comments = LGDCommentSerializer(many=True)


class LGDVariantGenCCConsequenceSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDVariantGenccConsequence model.
    """

    variant_consequence = serializers.CharField(source="variant_consequence.term")
    accession = serializers.CharField(
        source="variant_consequence.accession", required=False
    )  # curation/draft page doesn't input the accession
    support = serializers.CharField(source="support.value")
    publication = serializers.CharField(
        source="publication.pmid", allow_null=True, required=False
    )

    def create(self, validated_data):
        """
        Add a Variant GenCC consequence to a LGD record.

        Args:
            (dict) validated data: variant_consequence and support
            Example:
                    {
                        'support': 'inferred',
                        'variant_consequence': 'altered_gene_product_structure'
                    }

        Output:
            LGDVariantGenCCConsequence object

        Raises:
            Raise error if variant consequence term is invalid
            Raise error if support value is invalid
        """

        lgd = self.context["lgd"]
        term = validated_data.get("variant_consequence")["term"].replace("_", " ")
        support = validated_data.get("support")["value"].lower()

        # Get variant gencc consequence value from ontology_term
        # Possible values: absent gene product, altered gene product structure, etc.
        try:
            consequence_obj = OntologyTerm.objects.get(
                term=term,  # TODO check
                group_type__value="variant_type",
            )
        except OntologyTerm.DoesNotExist:
            raise serializers.ValidationError(
                {"message": f"Invalid variant consequence '{term}'"}
            )

        # Get support value from attrib
        # Values: evidence or inferred
        try:
            support_obj = Attrib.objects.get(value=support, type__code="support")
        except Attrib.DoesNotExist:
            raise serializers.ValidationError(
                {"message": f"Invalid support value '{support}'"}
            )

        # Check if the same term is already linked to the LGD record
        try:
            lgd_var_consequence_obj = LGDVariantGenccConsequence.objects.get(
                variant_consequence=consequence_obj, lgd=lgd
            )
        except LGDVariantGenccConsequence.DoesNotExist:
            lgd_var_consequence_obj = LGDVariantGenccConsequence.objects.create(
                variant_consequence=consequence_obj,
                support=support_obj,
                lgd=lgd,
                is_deleted=0,
            )
        else:
            # Check if existing entry is deleted
            # If not deleted throw error 'entry already exists'
            if lgd_var_consequence_obj.is_deleted == 0:
                raise serializers.ValidationError(
                    {
                        "message": f"'{term}' already linked to '{lgd.stable_id.stable_id}'"
                    }
                )
            # If deleted then update to not deleted
            else:
                lgd_var_consequence_obj.is_deleted = 0
                lgd_var_consequence_obj.save()

        return lgd_var_consequence_obj

    class Meta:
        model = LGDVariantGenccConsequence
        fields = ["variant_consequence", "accession", "support", "publication"]


class LGDVariantConsequenceListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of variant GenCC consequences.
    Called by: LGDAddVariantConsequences()
    """

    variant_consequences = LGDVariantGenCCConsequenceSerializer(many=True)


class LGDMechanismSynopsisSerializer(serializers.ModelSerializer):
    """
    Serializer for the MolecularMechanismSynopsis model.
    A molecular mechanism can have multiple synopsis.
    """

    synopsis = serializers.CharField(source="synopsis.value")
    synopsis_support = serializers.CharField(source="synopsis_support.value")

    def validate(self, data):
        lgd_instance = self.context["lgd"]
        synopsis_name = data["synopsis"]["value"]
        synopsis_support = data["synopsis_support"]["value"]
        mechanism_value = lgd_instance.mechanism.value

        # Get mechanism synopsis value from controlled vocabulary table for molecular mechanism
        try:
            data["synopsis"]["value"] = CVMolecularMechanism.objects.get(
                value=synopsis_name, type="mechanism_synopsis"
            )
        except CVMolecularMechanism.DoesNotExist:
            raise serializers.ValidationError(
                {"error": f"Invalid mechanism synopsis value '{synopsis_name}'"}
            )

        # Get mechanism synopsis support from controlled vocabulary table for molecular mechanism
        try:
            data["synopsis_support"]["value"] = CVMolecularMechanism.objects.get(
                value=synopsis_support, type="support"
            )
        except CVMolecularMechanism.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "error": f"Invalid mechanism synopsis support value '{synopsis_support}'"
                }
            )

        # Validate the synopsis
        if not validate_mechanism_synopsis(mechanism_value, synopsis_name):
            raise serializers.ValidationError(
                {
                    "error": f"The categorisation '{synopsis_name}' is not compatible with the mechanism '{mechanism_value}'. Please choose a categorisation relevant to the selected mechanism."
                }
            )

        return data

    def create(self, validate_data):
        """
        Create LGDMolecularMechanismSynopsis object
        """
        lgd_instance = self.context["lgd"]
        synopsis_obj = validate_data["synopsis"]["value"]
        synopsis_support_obj = validate_data["synopsis_support"]["value"]

        # Create new molecular mechanism
        mechanism_synopsis_obj = LGDMolecularMechanismSynopsis.objects.create(
            lgd=lgd_instance,
            synopsis=synopsis_obj,
            synopsis_support=synopsis_support_obj,
            is_deleted=0,
        )

        return mechanism_synopsis_obj

    class Meta:
        model = LGDMolecularMechanismSynopsis
        fields = ["synopsis", "synopsis_support"]


class EvidenceSerializer(serializers.Serializer):
    primary_type = serializers.CharField()
    secondary_type = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )


class LGDMechanismEvidenceSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDMolecularMechanismEvidence model.
    A molecular mechanism can have multiple evidence.
    """

    description = serializers.CharField(allow_blank=True)
    evidence = EvidenceSerializer()
    publication = serializers.CharField(source="publication.pmid")

    def create(self, validate_data):
        """
        Create LGDMolecularMechanismEvidence object
        """
        lgd_instance = self.context["lgd"]
        publication_instance = self.context["publication"]

        if validate_data["description"] == "":
            validate_data["description"] = None

        evidence_data = validate_data["evidence"]
        primary_type = evidence_data["primary_type"].lower().replace(" ", "_")
        secondary_type = evidence_data["secondary_type"]  # list of strings

        for evidence_value in secondary_type:
            # Get mechanism evidence value from the mechanism controlled vocabulary table
            try:
                evidence_obj = CVMolecularMechanism.objects.get(
                    value=evidence_value.lower(), type="evidence", subtype=primary_type
                )
            except CVMolecularMechanism.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid mechanism evidence value '{evidence_value}'"}
                )

            # Create new molecular mechanism evidence
            mechanism_evidence_obj = LGDMolecularMechanismEvidence.objects.create(
                lgd=lgd_instance,
                description=validate_data["description"],
                evidence=evidence_obj,
                publication=publication_instance,
                is_deleted=0,
            )

        return mechanism_evidence_obj

    class Meta:
        model = LGDMolecularMechanismEvidence
        fields = ["description", "evidence", "publication"]


class LGDCrossCuttingModifierSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDCrossCuttingModifier model.
    A G2P record can be linked to one or more cross cutting modifier.
    """

    term = serializers.CharField(source="ccm.value")

    def create(self, validate_data):
        """
        Add cross cutting modifier to LGD record.

        Args:
            (string) cross cutting modifier value

        Returns:
            LGDCrossCuttingModifier object

        Raises:
            Raise error if cross cutting modifier value is invalid
            Raise error if cross cutting modifier already linked to LGD record
        """

        lgd = self.context["lgd"]
        term_tmp = validate_data.get("ccm")["value"]
        term = term_tmp.replace("_", " ")

        # Get cross cutting modifier from attrib
        try:
            ccm_obj = Attrib.objects.get(
                value=term, type__code="cross_cutting_modifier"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError(
                {"message": f"Invalid cross cutting modifier '{term}'"}
            )

        # Check if LGD-cross cutting modifier already exists
        try:
            lgd_ccm_obj = LGDCrossCuttingModifier.objects.get(ccm=ccm_obj, lgd=lgd)
        except LGDCrossCuttingModifier.DoesNotExist:
            lgd_ccm_obj = LGDCrossCuttingModifier.objects.create(
                ccm=ccm_obj, lgd=lgd, is_deleted=0
            )
        else:
            # LGD-cross cutting modifier already exists
            # If not deleted then the entry already exists
            if lgd_ccm_obj.is_deleted == 0:
                raise serializers.ValidationError(
                    {
                        "message": f"G2P entry {lgd.stable_id.stable_id} is already linked to cross cutting modifier '{term}'"
                    }
                )
            else:
                # If deleted then update it to not deleted
                lgd_ccm_obj.is_deleted = 0
                lgd_ccm_obj.save()

        return lgd_ccm_obj

    class Meta:
        model = LGDCrossCuttingModifier
        fields = ["term"]


class LGDCrossCuttingModifierListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of cross cutting modifiers.
    Called by: LocusGenotypeDiseaseAddCCM()
    """

    cross_cutting_modifiers = LGDCrossCuttingModifierSerializer(many=True)


class LGDVariantTypeCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDVariantTypeComment model.
    Comment associated with the variant type that is linked to the G2P record.
    A comment can be public or private. Private comments can only be seen
    by curators.
    """

    comment = serializers.CharField()
    user = serializers.CharField(source="user.username")
    date = serializers.CharField()

    class Meta:
        model = LGDVariantTypeComment
        fields = ["comment", "user", "date"]


class LGDVariantTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDVariantType model.

    Types of variants reported in publications:
        missense_variant, frameshift_variant, stop_gained, etc.
    Sequence ontology terms are used to describe variant types.
    """

    term = serializers.CharField(source="variant_type_ot.term", required=False)
    accession = serializers.CharField(
        source="variant_type_ot.accession", required=False
    )  # Sequence ontology term
    inherited = serializers.BooleanField(allow_null=True)
    de_novo = serializers.BooleanField(allow_null=True)
    unknown_inheritance = serializers.BooleanField(allow_null=True)
    publication = serializers.IntegerField(
        source="publication.pmid", allow_null=True, required=False
    )
    comments = LGDVariantTypeCommentSerializer(many=True, required=False)
    # Extra fields for the create() method
    secondary_type = serializers.CharField(
        write_only=True
    )  # variant type term (used by curation)
    supporting_papers = serializers.ListField(
        write_only=True
    )  # list of pmids (used by curation)
    nmd_escape = serializers.BooleanField(write_only=True)  # flag (used by curation)
    comment = serializers.CharField(
        write_only=True, allow_blank=True
    )  # single comment (used by curation)

    def create(self, validated_data):
        """
        Method to create LGDVariantType object.
        A G2P record can be associated with one or more variant types.

        Returns:
                LGDVariantType object
        """

        user_obj = self.context["user"]
        lgd = self.context["lgd"]
        inherited = validated_data.get("inherited")
        de_novo = validated_data.get("de_novo")
        unknown_inheritance = validated_data.get("unknown_inheritance")
        var_type = validated_data.get("secondary_type", None)  # Used by curation
        publications = validated_data.get("supporting_papers", None)  # Used by curation
        comment = validated_data.get("comment", None)  # Used by curation

        # Get variant type from ontology_term
        # nmd_escape list: frameshift_variant, stop_gained, splice_region_variant?, splice_acceptor_variant,
        # splice_donor_variant
        # We save the variant types already with the NMD_escape attached to the term
        if validated_data.get("nmd_escape", None) is True:
            var_type = f"{var_type}_NMD_escaping"

        try:
            var_type_obj = OntologyTerm.objects.get(
                term=var_type, group_type__value="variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise serializers.ValidationError(
                {"message": f"Invalid variant type '{var_type}'"}
            )

        # Variants are supposed to be linked to publications
        # But if there is no publication then create the object without a pmid
        if not publications:
            # Check if entry exists in the table
            # An unique entry is defined by: lgd, variant_type and publication
            try:
                lgd_variant_type_obj = LGDVariantType.objects.get(
                    lgd=lgd, variant_type_ot=var_type_obj, publication=None
                )
            except LGDVariantType.DoesNotExist:
                lgd_variant_type_obj = LGDVariantType.objects.create(
                    lgd=lgd,
                    variant_type_ot=var_type_obj,
                    inherited=inherited,
                    de_novo=de_novo,
                    unknown_inheritance=unknown_inheritance,
                    is_deleted=0,
                )
            else:
                # the entry already exists, it probably needs to be updated
                # if deleted, set to not deleted
                if lgd_variant_type_obj.is_deleted == 1:
                    lgd_variant_type_obj.is_deleted = 0
                # update inheritance data
                if lgd_variant_type_obj.inherited == 0 and inherited == True:
                    lgd_variant_type_obj.inherited = 1
                if lgd_variant_type_obj.de_novo == 0 and de_novo == True:
                    lgd_variant_type_obj.de_novo = 1
                if (
                    lgd_variant_type_obj.unknown_inheritance == 0
                    and unknown_inheritance == True
                ):
                    lgd_variant_type_obj.unknown_inheritance = 1
                lgd_variant_type_obj.save()

            # The LGDPhenotypeSummary is created - next step is to create the LGDVariantTypeComment
            if comment != "":
                # Remove newlines from comment
                comment = re.sub(r"\n", " ", comment)
                try:
                    lgd_comment_obj = LGDVariantTypeComment.objects.get(
                        comment=comment,
                        lgd_variant_type=lgd_variant_type_obj,
                        is_public=0,  # variant type comments are private
                        user=user_obj,
                    )
                except LGDVariantTypeComment.DoesNotExist:
                    lgd_comment_obj = LGDVariantTypeComment.objects.create(
                        comment=comment,
                        lgd_variant_type=lgd_variant_type_obj,
                        is_public=0,  # variant type comments are private
                        is_deleted=0,
                        user=user_obj,
                        date=get_date_now(),
                    )
                else:
                    if lgd_comment_obj.is_deleted == 1:
                        lgd_comment_obj.is_deleted = 0
                        lgd_comment_obj.save()

        else:
            # Variant type is linked to publication(s)
            # A single variant type can be attached to several publications - create an object for each pmid
            for publication in publications:
                try:
                    # The publication is supposed to be stored in the G2P db
                    publication_obj = Publication.objects.get(pmid=publication)

                except Publication.DoesNotExist:
                    raise serializers.ValidationError(
                        {"message": f"Invalid publication '{publication}'"}
                    )

                else:
                    # The publication is valid
                    # Check if LGDVariantType object already exists in db
                    try:
                        lgd_variant_type_obj = LGDVariantType.objects.get(
                            lgd=lgd,
                            variant_type_ot=var_type_obj,
                            publication=publication_obj,
                        )
                    except LGDVariantType.DoesNotExist:
                        # Check if LGDVariantType object already exists in db without a publication
                        try:
                            lgd_variant_type_obj = LGDVariantType.objects.get(
                                lgd=lgd,
                                variant_type_ot=var_type_obj,
                                publication=None,  # no publication attached to entry
                                is_deleted=0,
                            )
                        except LGDVariantType.DoesNotExist:
                            # LGDVariantType does not exist with or without publication
                            # Create LGDVariantType object with publication
                            lgd_variant_type_obj = LGDVariantType.objects.create(
                                lgd=lgd,
                                variant_type_ot=var_type_obj,
                                inherited=inherited,
                                de_novo=de_novo,
                                unknown_inheritance=unknown_inheritance,
                                publication=publication_obj,
                                is_deleted=0,
                            )
                        else:
                            # LGDVariantType already exists in the db without a publication
                            # Add publication to existing object
                            lgd_variant_type_obj.publication = publication_obj
                            if (
                                lgd_variant_type_obj.inherited == False
                                and inherited == True
                            ):
                                lgd_variant_type_obj.inherited = True
                            if (
                                lgd_variant_type_obj.de_novo == False
                                and de_novo == True
                            ):
                                lgd_variant_type_obj.de_novo = True
                            if (
                                lgd_variant_type_obj.unknown_inheritance == False
                                and unknown_inheritance == True
                            ):
                                lgd_variant_type_obj.unknown_inheritance = True
                            lgd_variant_type_obj.save()
                    else:
                        # the entry already exists, it probably needs to be updated
                        # if deleted, set to not deleted
                        if lgd_variant_type_obj.is_deleted == 1:
                            lgd_variant_type_obj.is_deleted = 0
                        # update inheritance data
                        if (
                            lgd_variant_type_obj.inherited == False
                            and inherited == True
                        ):
                            lgd_variant_type_obj.inherited = True
                        if lgd_variant_type_obj.de_novo == False and de_novo == True:
                            lgd_variant_type_obj.de_novo = True
                        if (
                            lgd_variant_type_obj.unknown_inheritance == False
                            and unknown_inheritance == True
                        ):
                            lgd_variant_type_obj.unknown_inheritance = True
                        lgd_variant_type_obj.save()

                    # The LGDPhenotypeSummary is created - next step is to create the LGDVariantTypeComment
                    if comment != "":
                        # Remove newlines from comment
                        comment = re.sub(r"\n", " ", comment)
                        try:
                            lgd_comment_obj = LGDVariantTypeComment.objects.get(
                                comment=comment,
                                lgd_variant_type=lgd_variant_type_obj,
                                is_public=0,  # variant type comments are private
                                user=user_obj,
                            )
                        except LGDVariantTypeComment.DoesNotExist:
                            lgd_comment_obj = LGDVariantTypeComment.objects.create(
                                comment=comment,
                                lgd_variant_type=lgd_variant_type_obj,
                                is_public=0,  # variant type comments are private
                                is_deleted=0,
                                user=user_obj,
                                date=get_date_now(),
                            )
                        else:
                            if lgd_comment_obj.is_deleted == 1:
                                lgd_comment_obj.is_deleted = 0
                                lgd_comment_obj.save()

        return 1

    class Meta:
        model = LGDVariantType
        fields = [
            "term",
            "accession",
            "inherited",
            "de_novo",
            "unknown_inheritance",
            "publication",
            "comments",
            "secondary_type",
            "supporting_papers",
            "nmd_escape",
            "comment",
        ]


class LGDVariantTypeListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of variant types.
    Called by: LGDEditVariantTypes()
    """

    variant_types = LGDVariantTypeSerializer(many=True)


class LGDVariantTypeDescriptionSerializer(serializers.ModelSerializer):
    """
    The variant HGVS description is linked to:
        - LGD record (mandatory)
        - publication (mandatory)

    This serializer is called by curation and LGDAddVariantTypeDescriptions.
    In the curation data, the description is linked to one pmid (multiple pmids
    are represented multiple times attached to the same description).
    Meanwhile in LGDAddVariantTypeDescriptions the description is linked to a list of pmids.
    """

    publication = serializers.IntegerField(required=False)  # Used by curation
    description = serializers.CharField()  # HGVS description following HGVS standard
    # Extra fields for create() method
    publications = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )  # Used by views.LGDAddVariantTypeDescriptions

    def create(self, validated_data):
        """
        Method to create LGDVariantTypeDescription object.
        LGDVariantTypeDescription represents the variant HGVS
        linked to the LGD record and the publication.
        The HGVS is not directly linked to the variant type.

        Returns: 1

        Raises: Invalid publication
        """

        lgd = self.context["lgd"]
        publication = validated_data.get("publication")  # Used by curation
        description = validated_data.get("description")
        list_publications = validated_data.get(
            "publications", []
        )  # Used by views.LGDAddVariantTypeDescriptions

        # Create the list of pmids from the single publication sent by curation
        if not list_publications and publication:
            list_publications.append(publication)

        # Insert data based on the pmids
        # The variant description is supposed to be linked to publications
        for pmid in list_publications:
            try:
                publication_obj = Publication.objects.get(pmid=pmid)
            except Publication.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid publication '{publication}'"}
                )

            # Check if LGDVariantTypeDescription exists
            try:
                lgd_variant_type_desc = LGDVariantTypeDescription.objects.get(
                    lgd=lgd, description=description, publication=publication_obj
                )
            except LGDVariantTypeDescription.DoesNotExist:
                lgd_variant_type_desc = LGDVariantTypeDescription.objects.create(
                    lgd=lgd,
                    description=description,
                    publication=publication_obj,
                    is_deleted=0,
                )
            else:
                # If LGDVariantTypeDescription exists and it is deleted
                # then set existing entry to not deleted
                if lgd_variant_type_desc.is_deleted == 1:
                    lgd_variant_type_desc.is_deleted = 0
                    lgd_variant_type_desc.save()

        return 1

    class Meta:
        model = LGDVariantTypeDescription
        fields = ["publication", "description", "publications"]


class LGDVariantTypeDescriptionListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of variant type descriptions (HGVS).
    Called by: LGDAddVariantTypeDescriptions()
    """

    variant_descriptions = LGDVariantTypeDescriptionSerializer(many=True)


class LGDReviewSerializer(serializers.ModelSerializer):
    """
    Serializer to update the value of is_reviewed.
    """

    is_reviewed = serializers.BooleanField()

    def validate_is_reviewed(self, value: int) -> int:
        if value == self.instance.is_reviewed:
            state = "reviewed" if value else "under review"
            raise serializers.ValidationError(
                {
                    "error": f"{self.instance.stable_id.stable_id} is already set to {state}"
                }
            )
        return value

    def update(self, instance, validated_data):
        instance.is_reviewed = validated_data["is_reviewed"]
        # If the record is set to reviewed then update the date of the last review to today
        if validated_data["is_reviewed"]:
            instance.date_review = get_date_now()
        instance.save()
        return instance

    class Meta:
        model = LocusGenotypeDisease
        fields = ["is_reviewed"]
