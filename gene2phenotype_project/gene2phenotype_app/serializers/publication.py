from rest_framework import serializers
import re

from ..models import (
    Publication,
    PublicationComment,
    Attrib,
    LGDPublication
)

from ..utils import (
    get_publication,
    get_authors
)

from ..utils import get_date_now, clean_title


class PublicationCommentSerializer(serializers.ModelSerializer):
    """
        Serializer for the PublicationComment model.
        To insert a comment the user is fetched from the context.
        Publication comments are only available to authenticated users.
    """

    comment = serializers.CharField()
    date = serializers.DateTimeField()
    user = serializers.CharField(source="user.username")

    def create(self, data, publication):
        """
            Method to add a comment to a publication.
            The comment can be public or private.

            Returns:
                    PublicationComment object
        """

        comment_text = data.get("comment")
        user_obj = self.context['user'] # gets the user from the context
        is_public = 0 # publication comments are private

        # Remove newlines from comment
        comment_text = re.sub(r"\n", " ", comment_text)

        # Check if comment is already stored. We consider same comment if they have the same:
        #   publication, comment text, user and it's not deleted TODO
        # Filter can return multiple values - this can happen if we have duplicated entries
        publication_comment_list = PublicationComment.objects.filter(comment = comment_text,
                                                                     publication = publication,
                                                                     is_deleted = 0)

        # Comment was not found in table - insert new comment
        if not publication_comment_list:
            publication_comment_obj = PublicationComment.objects.create(comment = comment_text,
                                                                        is_public = is_public,
                                                                        is_deleted = 0,
                                                                        date = get_date_now(),
                                                                        publication = publication,
                                                                        user = user_obj)

        else:
            publication_comment_obj = publication_comment_list.first()

        return publication_comment_obj

    class Meta:
        model = PublicationComment
        fields = ["comment", "date", "user"]


class PublicationSerializer(serializers.ModelSerializer):
    """
        Serializer for the Publication model.
    """

    pmid = serializers.IntegerField()
    title = serializers.CharField(read_only=True)
    authors = serializers.CharField(read_only=True)
    year = serializers.CharField(read_only=True)
    comments = serializers.SerializerMethodField(allow_null=True)

    def get_comments(self, id):
        """
            Get all comments associated with the publication.

            Returns:
                    (list) comments: list of comments
        """

        user = self.context.get('user')

        # Authenticated users can view all types of comments
        if user and user.is_authenticated:
            queryset = PublicationComment.objects.filter(
                publication_id=id.id, is_deleted=0).prefetch_related('user')

        # Anonymous users can only view public comments
        else:
            queryset = PublicationComment.objects.filter(
                publication_id=id.id, is_deleted=0, is_public=1).prefetch_related('user')

        data = []

        for publication_comment in queryset:
            # Format the date
            date = None
            if publication_comment.date is not None:
                date = publication_comment.date.strftime("%Y-%m-%d")

            comment = {
                "comment": publication_comment.comment,
                "user": publication_comment.user.username,
                "date": date
            }
            data.append(comment)

        return data

    def validate(self, data):
        """
            Overwrite the validate method to accept extra fields:
             - comments
        """
        if hasattr(self, 'initial_data'):
            data = self.initial_data

        return data

    def create(self, validated_data):
        """
            Method to create a publication.
            If PMID is already stored in G2P, add the new comment to the existing PMID.
            This method is called when publishing a record.

            The PMID is mandatory, while comment is optional.

            Args:
                (dict) validated_data: valid PublicationSerializer fields 
                                       accepted fields are: pmid, comment
            
            Returns:
                    Publication object

            Raises:
                    Invalid PMID
        """
        pmid = validated_data['pmid'] # serializer fields
        comment = validated_data['comment'] # extra data - comment

        user_obj = self.context['user']

        try:
            publication_obj = Publication.objects.get(pmid=pmid)

        except Publication.DoesNotExist:
            response = get_publication(pmid)

            if response['hitCount'] == 0:
                raise serializers.ValidationError({"message": "Invalid PMID",
                                                   "Please check ID": pmid})

            authors = get_authors(response)
            year = None
            doi = None
            publication_info = response['result']
            title = clean_title(publication_info['title'])
            if 'doi' in publication_info:
                doi = publication_info['doi']
            if 'pubYear' in publication_info:
                year = publication_info['pubYear']

            # Insert publication
            publication_obj = Publication.objects.create(pmid = pmid,
                                                         title = title,
                                                         authors = authors,
                                                         year = year,
                                                         doi = doi)

        # Add new comment
        # Comment: {'comment': 'this is a comment', 'is_public': 1}
        if comment is not None:
            PublicationCommentSerializer(
                # the user is necessary to save the comment
                context={'user': user_obj}
            ).create(comment, publication_obj)

        return publication_obj

    class Meta:
        model = Publication
        fields = ['pmid', 'title', 'authors', 'year', 'comments']


### G2P record (LGD) - publication ###
class LGDPublicationSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDPublication model.
        Called by: LocusGenotypeDiseaseSerializer()
                   LGDPublicationListSerializer()
    """
    publication = PublicationSerializer()
    families = serializers.IntegerField(required=False, allow_null=True)
    consanguinity = serializers.CharField(source="consanguinity.value", required=False, allow_null=True)
    affected_individuals = serializers.IntegerField(required=False, allow_null=True)
    ancestries = serializers.CharField(required=False, allow_null=True)
    comment = serializers.DictField(required=False)

    def validate(self, data):
        """
            Overwrite the method to validate the data.
            This validate() method is activated by the curation (draft entry) endpoints and
            by the LGDPublicationListSerializer.
            This method is identical to the validate method in LGDPublicationListSerializer.
        """
        if hasattr(self, 'initial_data'):
            print("Validate LGDPublicationSerializer:", data)
            data = self.initial_data
            # valid_headers = ["families", "consanguinity", "ancestries", "affected_individuals"]
            # extra_headers = ["phenotypes", "variant_types", "variant_descriptions"]

            # # check if 'families' is defined in the initial data
            # # correct structure is: 
            # # { "families": 200, "consanguinity": "unknown", "ancestries": "african", 
            # #   "affected_individuals": 100 }
            # if "families" in self.initial_data and self.initial_data["families"] is not None:
            #     families = self.initial_data["families"] # If 'families' is in initial data then it cannot be null
            #     for header in families.keys():
            #         if header not in valid_headers:
            #             raise serializers.ValidationError(f"Got unknown field in families: {header}")

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

        publication_data = self.initial_data.get("publication") # 'publication': {'pmid': 39385417}
        # TODO: fix comment
        comment = self.initial_data.get('comment', None) # 'comment': {'comment': 'this is a comment', 'is_public': 1}
        families = publication_data.get("families", None)
        affected_individuals = publication_data.get("affected_individuals", None)
        ancestries = publication_data.get("ancestries", None)
        consanguinity = publication_data.get("consanguinity", None)
        consanguinity_obj = None

        print("Create LGDPublicationSerializer:", self.initial_data)

        # Get consanguinity from attrib
        if consanguinity:
            try:
                consanguinity_obj = Attrib.objects.get(
                    value = consanguinity,
                    type__code = "consanguinity"
                )
            except Attrib.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid consanguinity value {consanguinity}"}
                )

        if comment:
            comment_text = comment["comment"]

            # Check if comment text is empty string
            if not comment_text or comment_text == "":
                comment = None
            # Publication comments are always private
            else:
                comment["is_public"] = 0

        # it is necessary to send the user
        # the publication comment is linked to the user
        publication_serializer = PublicationSerializer(
            data={ 'pmid': publication_data.get('pmid'), 'comment': comment },
            context={ 'user': self.context.get('user') }
        )

        # Validate the input data
        if publication_serializer.is_valid(raise_exception=True):
            # save() is going to call create() method
            publication_obj = publication_serializer.save()

        try:
            lgd_publication_obj = LGDPublication.objects.get(
                lgd = lgd,
                publication = publication_obj
            )
        except LGDPublication.DoesNotExist:
            # Insert new LGD-publication entry
            lgd_publication_obj = LGDPublication.objects.create(
                lgd = lgd,
                publication = publication_obj,
                families = families,
                consanguinity = consanguinity_obj,
                affected_individuals = affected_individuals,
                ancestries = ancestries,
                is_deleted = 0
            )
        else:
            # LGD-publication already exists
            # If it does not have number of families or affected individuals then update it
            if not lgd_publication_obj.families or not lgd_publication_obj.affected_individuals:
                lgd_publication_obj.families = families
                lgd_publication_obj.affected_individuals = affected_individuals
                lgd_publication_obj.ancestries = ancestries
                lgd_publication_obj.consanguinity = consanguinity_obj
                lgd_publication_obj.save()

        # If LGD-publication already exists then returns the existing object
        # New comments are added to the existing object
        # If existing LGD-publication is deleted then update to not deleted
        if lgd_publication_obj.is_deleted != 0:
            lgd_publication_obj.is_deleted = 0
            lgd_publication_obj.save()

        return lgd_publication_obj

    class Meta:
        model = LGDPublication
        fields = ["publication", "families", "consanguinity", "affected_individuals", "ancestries", "comment"]


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
        if hasattr(self, 'initial_data'):
            data = self.initial_data
            # families_valid_headers = ["families", "consanguinity", "ancestries", "affected_individuals"]
            # extra_headers = ["phenotypes", "variant_types", "variant_descriptions"]

            # publications = self.initial_data.get("publications")

            # for publication_obj in publications:
            #     publication = publication_obj.get("publication")

            #     # check if 'families' is defined
            #     # correct structure is: 
            #     # "families": { "families": 2, "consanguinity": "unknown", "ancestries": "african", "affected_individuals": 1 }
            #     if "families" in publication:
            #         families = publication.get("families")
            #         for header in families.keys():
            #             if header not in families_valid_headers:
            #                 raise serializers.ValidationError(f"Got unknown field in families: {header}")

                # TODO check if 'comment' is defined
                # if "comment" in publication:
                #     comment = publication.get("comment")

        return data