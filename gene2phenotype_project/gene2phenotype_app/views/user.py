from rest_framework import generics
from rest_framework.response import Response

from gene2phenotype_app.serializers import UserSerializer

from gene2phenotype_app.models import User


class UserList(generics.ListAPIView):
    serializer_class = UserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user_login':self.request.user})
        return context

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            queryset = User.objects.filter(is_active=1)
        else:
            queryset = User.objects.filter(is_active=1, is_staff=0)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True, context={'user': self.request.user})

        return Response({'results': serializer.data, 'count':len(serializer.data)})
