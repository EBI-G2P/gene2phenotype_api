from rest_framework import serializers
import re

from ..models import Publication, LGDPublicationComment, Attrib, LGDPublication

from ..utils import get_publication, get_authors

from ..utils import get_date_now, clean_title


class LGDPublicationCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDPublicationComment model.
    To insert a comment the user is fetched from the context.
    Publication comments are only available to authenticated users.
    """
    comment = serializers.CharField()
    date = serializers.DateTimeField(read_only=True)
    user = serializers.CharField(source="user.username", read_only=True)

    def create(self, data):
        """
        Method to add a comment to a lgd-publication.
        The publication comments are always private.

        Returns:
                LGDPublicationComment object
        """
        comment_text = data.get("comment")
        user_obj = self.context["user"] # gets the user from the context
        lgd_publication_obj = self.context["lgd_publication"]
        is_public = 0  # publication comments are private

        # Remove newlines from comment
        comment_text = re.sub(r"\n", " ", comment_text)

        # Check if comment is already stored. We consider same comment if they have the same:
        #   lgd-publication, comment text and it is not deleted
        # Filter can return multiple values - this can happen if we have duplicated entries
        publication_comment_list = LGDPublicationComment.objects.filter(
            lgd_publication=lgd_publication_obj,
            comment=comment_text,
            is_deleted=0
        )

        # Comment was not found in table - insert new comment
        if not publication_comment_list:
            publication_comment_obj = LGDPublicationComment.objects.create(
                lgd_publication=lgd_publication_obj,
                comment=comment_text,
                is_public=is_public,
                is_deleted=0,
                date=get_date_now(),
                user=user_obj,
            )

        else:
            publication_comment_obj = publication_comment_list.first()

        return publication_comment_obj

    class Meta:
        model = LGDPublicationComment
        fields = ["comment", "date", "user"]


class PublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Publication model.
    """
    pmid = serializers.IntegerField()
    title = serializers.CharField(read_only=True)
    authors = serializers.CharField(read_only=True)
    year = serializers.CharField(read_only=True)

    def create(self, validated_data):
        """
        Method to create a publication.
        This method is called when publishing a record.
        The PMID is mandatory.

        Args:
            (dict) validated_data: valid PublicationSerializer fields
                                   accepted fields are: pmid

        Returns:
                Publication object

        Raises:
                Invalid PMID
        """
        pmid = validated_data["pmid"]  # serializer fields

        try:
            publication_obj = Publication.objects.get(pmid=pmid)

        except Publication.DoesNotExist:
            response = get_publication(pmid)

            if response["hitCount"] == 0:
                raise serializers.ValidationError(
                    {"error": f"Invalid PMID {pmid}"}
                )

            authors = get_authors(response)
            year = None
            doi = None
            publication_info = response["result"]
            title = clean_title(publication_info["title"])
            if "doi" in publication_info:
                doi = publication_info["doi"]
            if "pubYear" in publication_info:
                year = publication_info["pubYear"]

            # Insert publication
            publication_obj = Publication.objects.create(
                pmid=pmid, title=title, authors=authors, year=year, doi=doi
            )

        return publication_obj

    class Meta:
        model = Publication
        fields = ["pmid", "title", "authors", "year"]


### G2P record (LGD) - publication ###
class LGDPublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDPublication model.
    Called by: LocusGenotypeDiseaseSerializer()
               LGDPublicationListSerializer()
    """
    publication = PublicationSerializer()
    number_of_families = serializers.IntegerField(required=False, allow_null=True)
    consanguinity = serializers.CharField(
        source="consanguinity.value", required=False, allow_null=True
    )
    affected_individuals = serializers.IntegerField(required=False, allow_null=True)
    ancestry = serializers.CharField(required=False, allow_null=True)
    comments = serializers.SerializerMethodField(allow_null=True)

    def get_comments(self, id):
        """
        Get all comments associated with the LGD-publication.

        Returns:
            (list) comments: list of comments
        """
        user = self.context.get("user")

        # Authenticated users can view all types of comments
        if user and user.is_authenticated:
            queryset = LGDPublicationComment.objects.filter(
                lgd_publication_id=id, is_deleted=0
            ).prefetch_related("user")

        # Anonymous users can only view public comments
        else:
            queryset = LGDPublicationComment.objects.filter(
                lgd_publication_id=id, is_deleted=0, is_public=1
            ).prefetch_related("user")

        data = []

        for publication_comment in queryset:
            # Format the date
            date = None
            if publication_comment.date is not None:
                date = publication_comment.date.strftime("%Y-%m-%d")

            comment = {
                "comment": publication_comment.comment,
                "user": publication_comment.user.username,
                "date": date,
            }
            data.append(comment)

        return data

    def validate(self, data):
        """
        Overwrite the method to validate the data.
        This validate() method is activated by the curation endpoints and
        by the LGDPublicationListSerializer.
        This method is identical to the validate method in LGDPublicationListSerializer.
        """
        if hasattr(self, "initial_data"):
            data = self.initial_data

            # Check the format when sent by curation
            # Expected format:
            # {'publication': {'pmid': '1',
            # 'comment': {'comment': 'PMID:1 has two affected individuals from the same family', 'is_public': 1},
            # 'number_of_families': 1, 'consanguinity': 'yes', 'ancestry': 'european', 'affected_individuals': 2}}
            if "number_of_families" in self.initial_data["publication"]:
                data["number_of_families"] = self.initial_data["publication"][
                    "number_of_families"
                ]
                data["consanguinity"] = self.initial_data["publication"][
                    "consanguinity"
                ]
                data["ancestry"] = self.initial_data["publication"]["ancestry"]
                data["affected_individuals"] = self.initial_data["publication"][
                    "affected_individuals"
                ]

            # Check the format when sent by 'add publications'
            # Expected format:
            # {'publication': {'pmid': '2'},
            # 'comment': {'comment': 'comment for the PMID:2', 'is_public': 1},
            # 'families': {'families': 2, 'consanguinity': 'unknown', 'ancestries': '', 'affected_individuals': 2}}
            if "families" in self.initial_data:
                data["number_of_families"] = self.initial_data["families"]["families"]
                data["consanguinity"] = self.initial_data["families"]["consanguinity"]
                data["ancestry"] = self.initial_data["families"]["ancestries"]
                data["affected_individuals"] = self.initial_data["families"][
                    "affected_individuals"
                ]

        return data

    def create(self, validated_data):
        """
        Method to create LGD-publication associations.
        Extra data ('comment') can be inputted as context or
        as part of the serializer fields.

        Args:
            (dict) validate_data: accepted field is 'publication'
            Example input data:
                                {'publication': {'pmid': 1}}

        Returns:
                LGDPublication object
        """
        lgd = self.context["lgd"]
        user_obj = self.context["user"]

        # Format: {'publication': {'pmid': 39385417}}
        publication_data = validated_data.get("publication")
        # Format: {'comment': {'comment': 'this is a comment', 'is_public': 0}}
        comment = validated_data.get("comment", None)
        comment_text = None

        # The families format can be different depending on the type of update
        number_of_families = validated_data.get("number_of_families", None)
        affected_individuals = validated_data.get("affected_individuals", None)
        ancestry = validated_data.get("ancestry", None)
        consanguinity = validated_data.get("consanguinity", None)
        consanguinity_obj = None

        # Check if ancestry is empty string
        if ancestry == "":
            ancestry = None

        # Get consanguinity from attrib
        if consanguinity:
            try:
                consanguinity_obj = Attrib.objects.get(
                    value=consanguinity, type__code="consanguinity"
                )
            except Attrib.DoesNotExist:
                raise serializers.ValidationError(
                    {"error": f"Invalid consanguinity value '{consanguinity}'"}
                )

        if comment:
            comment_text = comment["comment"]
            # Check if comment text is empty string
            if not comment_text or comment_text == "":
                comment_text = None

        publication_serializer = PublicationSerializer(
            data={"pmid": publication_data.get("pmid")},
        )

        # Validate the input data
        if publication_serializer.is_valid(raise_exception=True):
            # save() is going to call create() method
            publication_obj = publication_serializer.save()

        try:
            lgd_publication_obj = LGDPublication.objects.get(
                lgd=lgd, publication=publication_obj
            )
        except LGDPublication.DoesNotExist:
            # Insert new LGD-publication entry
            lgd_publication_obj = LGDPublication.objects.create(
                lgd=lgd,
                publication=publication_obj,
                number_of_families=number_of_families,
                consanguinity=consanguinity_obj,
                affected_individuals=affected_individuals,
                ancestry=ancestry,
                is_deleted=0,
            )
            if comment_text:
                # Insert LGD-publication-comment entry
                lgd_publication_comment_serializer = LGDPublicationCommentSerializer(
                    data={"comment": comment_text},
                    context={"user": user_obj, "lgd_publication": lgd_publication_obj},
                )
                if lgd_publication_comment_serializer.is_valid(raise_exception=True):
                    # save() is going to call create() method
                    lgd_publication_comment_serializer.save()
                else:
                    print("Error adding lgdpublication-comment")
        else:
            # LGD-publication already exists
            # If it does not have number of families or affected individuals then update it
            if (
                not lgd_publication_obj.number_of_families
                or not lgd_publication_obj.affected_individuals
            ):
                lgd_publication_obj.number_of_families = number_of_families
                lgd_publication_obj.affected_individuals = affected_individuals
                lgd_publication_obj.ancestry = ancestry
                lgd_publication_obj.consanguinity = consanguinity_obj
                lgd_publication_obj.save()

            # Insert comment to existing publication
            if comment_text:
                # Insert LGD-publication-comment entry
                lgd_publication_comment_serializer = LGDPublicationCommentSerializer(
                    data={"comment": comment_text},
                    context={"user": user_obj, "lgd_publication": lgd_publication_obj},
                )
                if lgd_publication_comment_serializer.is_valid(raise_exception=True):
                    # save() is going to call create() method
                    lgd_publication_comment_serializer.save()
                else:
                    print("Error adding lgdpublication-comment")

        # If LGD-publication already exists then returns the existing object
        # New comments are added to the existing object
        # If existing LGD-publication is deleted then update to not deleted
        if lgd_publication_obj.is_deleted != 0:
            lgd_publication_obj.is_deleted = 0
            lgd_publication_obj.save()

        return lgd_publication_obj

    class Meta:
        model = LGDPublication
        fields = [
            "publication",
            "number_of_families",
            "consanguinity",
            "affected_individuals",
            "ancestry",
            "comments",
        ]


class LGDPublicationListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of publications.
    This method only validates the publications, it does not update any data.
    Called by: LocusGenotypeDiseaseAddPublication() and view LGDEditPublications()
    """
    publications = LGDPublicationSerializer(many=True)

    def validate(self, data):
        """
        Overwrite the method to validate the data.
        If the data is valid, return the initial data.
        This validate() method is activated by the endpoint that add/remove publication(s)
        """
        # self.initial_data contains extra fields sent to the serializer
        # comments and families are extra fields
        # by default these fields are not accepted as valid as they are not part of the LGDPublication
        if hasattr(self, "initial_data"):
            data = self.initial_data

        return data
