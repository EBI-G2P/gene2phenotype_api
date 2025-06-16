from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework import status

from gene2phenotype_app.serializers import GenCCSubmissionSerializer, G2PStableIDSerializer, CreateGenCCSubmissionSerializer

class GenCCSubmissionCreateView(generics.CreateAPIView):
    serializer_class = CreateGenCCSubmissionSerializer
    permission_classes = [permissions.IsAdminUser]

class GenCCSubmissionView(APIView):
    """GenCCSubmissionView 
    """    
    def get(self, request) -> Response:
        """Gets the unsubmitted stable ids

        Returns:
            Response: Response containing the status and the serializer.data
        """        
        unused_ids = GenCCSubmissionSerializer.fetch_list_of_unsubmitted_stable_id()
        serializer = G2PStableIDSerializer(unused_ids, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class StableIDsWithLaterReviewDateView(APIView):
    """StableIDs with laterReview date
    """    
    def get(self, request)-> Response:
        """Gets the Stable IDs that were reviewed later

        Returns:
            Response: Response object containing the 
             stable_ids as a list 
             the count of stable_ids that fit this criteria 
             status
        """        
        stable_ids = GenCCSubmissionSerializer.fetch_stable_ids_with_later_review_date()
        return Response({"stable_ids": list(stable_ids), "count": len(list(stable_ids))}, status=status.HTTP_200_OK)