from rest_framework import serializers
from datetime import datetime

from ..models import (Publication, PublicationComment,
                      PublicationFamilies, Attrib, LGDPublication)
from ..utils import (get_publication, get_authors)


class PublicationCommentSerializer(serializers.ModelSerializer):
    """
        Serializer for the PublicationComment model.
        To insert a comment the user is fetched from the context.
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
        is_public = data.get("is_public")
        user_obj = self.context['user'] # gets the user from the context

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
                                                                        date = datetime.now(),
                                                                        publication = publication,
                                                                        user = user_obj)

        else:
            publication_comment_obj = publication_comment_list.first()

        return publication_comment_obj

    class Meta:
        model = PublicationComment
        fields = ["comment", "date", "user"]

class PublicationFamiliesSerializer(serializers.ModelSerializer):
    """
        Serializer for the PublicationFamilies model.
    """

    families = serializers.IntegerField()
    affected_individuals = serializers.IntegerField(required=False, allow_null=True)
    ancestries = serializers.CharField(required=False, allow_null=True)
    consanguinity = serializers.CharField(source="consanguinity.value", required=False, allow_null=True)

    def create(self, validated_data, publication):
        """
            Method to add the information about the families reported in the publication.

            Args:
                - families: number of families reported in the publication (mandatory)
                - consanguinity: consanguinity (default: unknown)
                - ancestries: ancestry free text
                - affected_individuals: number of affected individuals reported in the publication
            
            Returns:
                    PublicationFamilies object

            Raises:
                    Invalid consanguinity value
        """

        families = validated_data.get("families")
        ancestries = validated_data.get("ancestries")
        affected_individuals = validated_data.get("affected_individuals")

        # Check the consanguinity value (optional)
        consanguinity_obj = None
        if "consanguinity" in validated_data:
            consanguinity = validated_data.get("consanguinity")

            # Get consanguinity from attrib
            try:
                consanguinity_obj = Attrib.objects.get(
                    value = consanguinity,
                    type__code = "consanguinity"
                )
            except Attrib.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Invalid consanguinity value {consanguinity}"}
                )

        # Check if LGD-publication families is already stored
        # TODO check what defines as already stored - if paper already has family data then it should be enough
        try:
            publication_families_obj = PublicationFamilies.objects.get(
                publication = publication,
                families = families,
                consanguinity = consanguinity_obj,
                ancestries = ancestries,
                affected_individuals = affected_individuals
            )

        except PublicationFamilies.DoesNotExist:
            # Data was not found in table - insert families data
            publication_families_obj = PublicationFamilies.objects.create(
                publication = publication,
                families = families,
                consanguinity = consanguinity_obj,
                ancestries = ancestries,
                affected_individuals = affected_individuals
            )

        return publication_families_obj

    class Meta:
        model = PublicationFamilies
        fields = ["families", "affected_individuals", "ancestries", "consanguinity"]

class PublicationSerializer(serializers.ModelSerializer):
    """
        Serializer for the Publication model.
    """

    pmid = serializers.IntegerField()
    title = serializers.CharField(read_only=True)
    authors = serializers.CharField(read_only=True)
    year = serializers.CharField(read_only=True)
    comments = serializers.SerializerMethodField(allow_null=True)
    families = serializers.SerializerMethodField(allow_null=True)

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
            comment = {
                "comment": publication_comment.comment,
                "user": publication_comment.user.username,
                "date": publication_comment.date
            }
            data.append(comment)

        return data

    def get_families(self, id):
        """
            Get families info reported in the publication.

            Returns:
                    (list) families: list of families
        """

        queryset = PublicationFamilies.objects.filter(publication_id=id.id, is_deleted=0).prefetch_related('consanguinity')
        data = []

        for publication_family in queryset:
            # Check if consanguinity is NULL
            if publication_family.consanguinity is None:
                consanguinity = None
            else:
                consanguinity = publication_family.consanguinity.value

            families = {
                "number_of_families": publication_family.families,
                "affected_individuals": publication_family.affected_individuals,
                "ancestry": publication_family.ancestries,
                "consanguinity": consanguinity
            }
            data.append(families)

        return data

    def validate(self, data):
        """
            Overwrite the validate method to accept extra fields:
             - comments
             - families
        """
        if hasattr(self, 'initial_data'):
            data = self.initial_data

        return data

    def create(self, validated_data):
        """
            Method to create a publication.
            If PMID is already stored in G2P, add the new comment and number of 
            families to the existing PMID.
            This method is called when publishing a record.

            The extra fields 'comment' and 'families' are passed in the context.

            Args:
                (dict) validated_data: valid PublicationSerializer fields 
                                       accepted fields are: pmid, title, authors, year
            
            Returns:
                    Publication object

            Raises:
                    Invalid PMID
        """
        pmid = validated_data.get('pmid') # serializer fields
        comment = validated_data.get('comment') # extra data - comment
        number_of_families = validated_data.get('families') # extra data - families reported in publication

        user_obj = self.context.get('user')

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
            title = publication_info['title']
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

        # Add family info linked to publication
        if number_of_families is not None:
            PublicationFamiliesSerializer().create(number_of_families, publication_obj)

        return publication_obj

    class Meta:
        model = Publication
        fields = ['pmid', 'title', 'authors', 'year', 'comments', 'families']

### G2P record (LGD) - publication ###
class LGDPublicationSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDPublication model.
        Called by: LocusGenotypeDiseaseSerializer()
                   LGDPublicationListSerializer()
    """
    publication = PublicationSerializer()
    comment = serializers.DictField(required=False)
    families = serializers.DictField(required=False)

    def validate(self, data):
        """
            Overwrite the method to validate the data.
            This validate() method is activated by the curation (draft entry) endpoints and
            by the LGDPublicationListSerializer.
            This method is identical to the validate method in LGDPublicationListSerializer.
        """
        if hasattr(self, 'initial_data'):
            data = self.initial_data
            valid_headers = ["families", "consanguinity", "ancestries", "affected_individuals"]
            extra_headers = ["phenotypes", "variant_types", "variant_descriptions"]

            # check if 'families' is defined in the initial data
            # correct structure is: 
            # { "families": 200, "consanguinity": "unknown", "ancestries": "african", 
            #   "affected_individuals": 100 }
            if "families" in self.initial_data:
                families = self.initial_data.get("families") # If 'families' is in initial data then it cannot be null
                for header in families.keys():
                    if header not in valid_headers:
                        raise serializers.ValidationError(f"Got unknown field in families: {header}")

        return data

    def create(self, validated_data):
        """
            Method to create LGD-publication associations.
            Extra data ('comment', 'families') can be inputted as context or
            as part of the serializer fields.

            Args:
                (dict) validate_data: accepted field is 'publication'
                Example input data:
                                    {'publication': {'pmid': 1}}

            Returns:
                    LGDPublication object
        """

        lgd = self.context['lgd']
        comment = None
        families = None

        publication_data = self.initial_data.get('publication') # 'publication': {'pmid': 39385417}
        comment = self.initial_data.get('comment', None) # 'comment': {'comment': 'this is a comment', 'is_public': 1}
        families = self.initial_data.get("families", None) # "families": { "families": 200, "consanguinity": "unknown", "ancestries": "african", "affected_individuals": 2 }

        if comment:
            comment_text = comment.get("comment", None)

            # Check if comment text is empty string
            if not comment_text or comment_text == "":
                comment = None
            # If 'is_public' is not defined set it to public (default)
            else:
                comment["is_public"] = comment.get("is_public", 1)

        # it is necessary to send the user
        # the publication comment is linked to the user
        publication_serializer = PublicationSerializer(
            data={ 'pmid': publication_data.get('pmid'), 'families': families, 'comment': comment },
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
                is_deleted = 0
            )

        # If LGD-publication already exists then returns the existing object
        # New comments and/or family info are added to the existing object
        # If existing LGD-publication is deleted then update to not deleted
        if lgd_publication_obj.is_deleted != 0:
            lgd_publication_obj.is_deleted = 0
            lgd_publication_obj.save()

        # When we add a publication to a LGD record, we should also link the new publication to
        # other existing/new data (LGDPhenotype, LGDPhenotypeSummary, LGDVariantType, LGDVariantTypeDescription)
        

        return lgd_publication_obj

    class Meta:
        model = LGDPublication
        fields = ['publication', 'comment', 'families']

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
            families_valid_headers = ["families", "consanguinity", "ancestries", "affected_individuals"]
            extra_headers = ["phenotypes", "variant_types", "variant_descriptions"]

            publications = self.initial_data.get("publications")

            for publication_obj in publications:
                publication = publication_obj.get("publication")

                # check if 'families' is defined
                # correct structure is: 
                # "families": { "families": 2, "consanguinity": "unknown", "ancestries": "african", "affected_individuals": 1 }
                if "families" in publication:
                    families = publication.get("families")
                    for header in families.keys():
                        if header not in families_valid_headers:
                            raise serializers.ValidationError(f"Got unknown field in families: {header}")

                # TODO check if 'comment' is defined
                # if "comment" in publication:
                #     comment = publication.get("comment")

        return data