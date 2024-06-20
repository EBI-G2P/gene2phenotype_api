from rest_framework import serializers
from datetime import datetime

from ..models import Publication, PublicationComment, PublicationFamilies, Attrib
from ..utils import (get_publication, get_authors)


class PublicationCommentSerializer(serializers.ModelSerializer):

    def create(self, data, publication):
        comment_text = data.get("comment")
        is_public = data.get("is_public")
        user_obj = self.context['user']

        # Check if comment is already stored. We consider same comment if they have the same:
        #   publication, comment text, user and it's not deleted TODO
        # Filter can return multiple values - this can happen if we have duplicated entries
        publication_comment_list = PublicationComment.objects.filter(comment = comment_text,
                                                                     user = user_obj,
                                                                     is_deleted = 0)

        publication_comment_obj = publication_comment_list.first()

        # Comment was not found in table - insert new comment
        if len(publication_comment_list) == 0:
            publication_comment_obj = PublicationComment.objects.create(comment = comment_text,
                                                                        is_public = is_public,
                                                                        is_deleted = 0,
                                                                        date = datetime.now(),
                                                                        publication = publication,
                                                                        user = user_obj)

        return publication_comment_obj

    class Meta:
        model = PublicationComment

class PublicationFamiliesSerializer(serializers.ModelSerializer):

    def create(self, validated_data, publication):
        """
            Create a PublicationFamilies object.

            Fields:
                    - families: number of families reported in the publication (mandatory)
                    - consanguinity: consanguinity (default: unknown)
                    - ancestries: ancestry free text
                    - affected_individuals: number of affected individuals reported in the publication
        """
        families = validated_data.get("families")
        consanguinity = validated_data.get("consanguinity")
        ancestries = validated_data.get("ancestries")
        affected_individuals = validated_data.get("affected_individuals")

        # Check if there is data
        if families == "" or families is None:
            return None

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

class PublicationSerializer(serializers.ModelSerializer):
    pmid = serializers.IntegerField()
    title = serializers.CharField(read_only=True)
    authors = serializers.CharField(read_only=True)
    year = serializers.CharField(read_only=True)
    comments = PublicationCommentSerializer(many=True, required=False)
    number_of_families = PublicationFamiliesSerializer(many=True, required=False)

    def create(self, validated_data):
        """
            Create a publication.
            If PMID is already stored in G2P, add the new comment and number of 
            families to the existing PMID.
            This method is called when publishing a record.

            Fields:
                    - pmid: publications PMID (mandatory)
                    - comments: list of comments
                    - number_of_families: list of families
        """

        pmid = validated_data.get('pmid')
        comments = validated_data.get('comments')
        number_of_families = validated_data.get('number_of_families')

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

        # Add new comments and/or number of families
        for comment in comments:
            if comment != "":
                PublicationCommentSerializer(
                    context={'user': self.context.get('user')}
                ).create(comment, publication_obj)

        for family in number_of_families:
            PublicationFamiliesSerializer().create(family, publication_obj)

        return publication_obj

    class Meta:
        model = Publication
        fields = ['pmid', 'title', 'authors', 'year', 'comments', 'number_of_families']
