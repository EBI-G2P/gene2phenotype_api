from rest_framework import serializers
from ..models import GenCCSubmission, G2PStableID, LocusGenotypeDisease
from django.db.models import OuterRef, Exists, Subquery, DateField, ExpressionWrapper, F
from typing import Any
from django.db.models.query import QuerySet



class GenCCSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for the GenCCSubmission
    """    
    def create(self, validated_data: dict[str, Any]) -> GenCCSubmission:
        """Create for the GenCC submission

        Args:
            validated_data (dict[str, Any]): Validated data dictionary

        Returns:
            GenCCSubmission: A created GenCC submission object
        """        
        return GenCCSubmission.objects.create(**validated_data)

    @staticmethod
    def fetch_list_of_unsubmitted_stable_id() -> QuerySet:
        """Fetch List of unsubmitted stable id from the G2PStableID by comparing whats in the GenCCSubmission table

        Returns:
            QuerySet: A queryset
        """           
        return G2PStableID.objects.annotate(
            has_submission=Exists(
                GenCCSubmission.objects.filter(g2p_stable_id=OuterRef('id'))
            )
        ).filter(has_submission=False, is_live=1)

  
    
    @staticmethod
    def fetch_stable_ids_with_later_review_date() -> QuerySet:
        """Fetches Stable ID that has been updated since the last GenCC submission

        Returns:
            QuerySet: A queryset
        """        
        
        return G2PStableID.objects.filter(
            Exists(
                LocusGenotypeDisease.objects.filter(
                    stable_id=OuterRef('id'),
                    date_review__gt=Subquery(
                        GenCCSubmission.objects.filter(
                            g2p_stable_id=OuterRef('id')
                        ).values('date_of_submission')[:1]
                    )
                )
            )
        ).values_list('stable_id', flat=True)

    

    
