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
                                                                     user = user_obj,
                                                                     is_deleted = 0)

        # Comment was not found in table - insert new comment
        if len(publication_comment_list) == 0:
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
    affected_individuals = serializers.IntegerField(required=False)
    ancestries = serializers.CharField(required=False)
    consanguinity = serializers.CharField(source="consanguinity.value", required=False)

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
        consanguinity = validated_data.get("consanguinity")
        ancestries = validated_data.get("ancestries")
        affected_individuals = validated_data.get("affected_individuals")

        # Get consanguinity from attrib
        try:
            consanguinity_obj = Attrib.objects.get(
                value = consanguinity,
                type__code = "consanguinity"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid consanguinity value {consanguinity}"})

        # Check if LGD-publication families is already stored
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

        queryset = PublicationComment.objects.filter(publication_id=id.id, is_deleted=0).prefetch_related('user')
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
            families = {
                "number_of_families": publication_family.families,
                "affected_individuals": publication_family.affected_individuals,
                "ancestry": publication_family.ancestries,
                "consanguinity": publication_family.consanguinity.value
            }
            data.append(families)

        return data

    def create(self, validated_data):
        """
            Method to create a publication.
            If PMID is already stored in G2P, add the new comment and number of 
            families to the existing PMID.
            This method is called when publishing a record.

            The extra fields 'comments' and 'families' are passed in the context.

            Args:
                (dict) validated_data: valid PublicationSerializer fields 
                                       accepted fields are: pmid, title, authors, year
            
            Returns:
                    Publication object

            Raises:
                    Invalid PMID
        """

        pmid = validated_data.get('pmid') # serializer fields
        comment = self.context.get('comment') # extra data - comment
        number_of_families = self.context.get('families') # extra data - families reported in publication

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
                context={'user': self.context.get('user')}
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
    """
    publication = PublicationSerializer()

    def create(self, validated_data):
        """
            Method to create LGD-publication associations.
            Extra data ('comment', 'families') is passed as context.

            Args:
                (dict) validate_data: accepted fied is 'publication'
                Example input data:
                                    {'publication': {'pmid': 1}}

            Returns:
                    LGDPublication object
        """

        lgd = self.context['lgd']
        comment = self.context['comment'] # extra data - comment
        families = self.context['families'] # extra data - families reported in publication
        publication_data = validated_data.get('publication') # only includes the publication pmid

        # it is necessary to send the user
        # the publication comment is linked to the user
        publication_serializer = PublicationSerializer(
            data={ 'pmid': publication_data.get('pmid') },
            context={ 'comment': comment, 'families': families, 'user': self.context.get('user') }
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

        else:
            # If LGD-publication is not deleted then throw validation error
            if lgd_publication_obj.is_deleted == 0:
                raise serializers.ValidationError(
                    {"message": f"Record {lgd.stable_id.stable_id} is already linked to publication '{publication_obj.pmid}'"}
                )
            else:
                # If LGD-publication is deleted then update to not deleted
                lgd_publication_obj.is_deleted = 0
                lgd_publication_obj.save()

        return lgd_publication_obj

    class Meta:
        model = LGDPublication
        fields = ['publication']
