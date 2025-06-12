from rest_framework import serializers
from ..models import GenCCSubmission, G2PStableID, LocusGenotypeDisease
from django.db.models import OuterRef, Exists, Subquery, DateField, ExpressionWrapper, F



class GenCCSubmissionSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        return GenCCSubmission.objects.create(**validated_data)

    @staticmethod
    def fetch_list_of_unsubmitted_stable_id():
        return G2PStableID.objects.annotate(
            has_submission=Exists(
                GenCCSubmission.objects.filter(g2p_stable_id=OuterRef('id'))
            )
        ).filter(has_submission=False, is_live=1)

    
    @staticmethod
    def fetch_stable_ids_with_later_review_date():
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

    

    
