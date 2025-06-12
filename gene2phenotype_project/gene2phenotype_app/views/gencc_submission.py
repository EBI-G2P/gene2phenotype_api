from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from gene2phenotype_app.serializers import GenCCSubmissionSerializer, G2PStableIDSerializer

class GenCCSubmissionView(APIView):
    def get(self, request):
        unused_ids = GenCCSubmissionSerializer.fetch_list_of_unsubmitted_stable_id()
        serializer = G2PStableIDSerializer(unused_ids, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class StableIDsWithLaterReviewDateView(APIView):
    def get(self, request):
        stable_ids = GenCCSubmissionSerializer.fetch_stable_ids_with_later_review_date()
        return Response({"stable_ids": list(stable_ids), "count": len(list(stable_ids))}, status=status.HTTP_200_OK)