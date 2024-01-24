from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from gene2phenotype_app import views

def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

# specify URL Path for rest_framework
urlpatterns = [
    path('gene2phenotype/api/panel/', views.PanelList.as_view(), name="list_panels"),
]

urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns += [
    path('api-auth/', include('rest_framework.urls'))
]