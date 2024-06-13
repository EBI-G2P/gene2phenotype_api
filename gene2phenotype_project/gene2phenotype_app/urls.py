from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from gene2phenotype_app import views

def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

# specify URL Path for rest_framework
urlpatterns = [
    path('gene2phenotype/api/panels/', views.PanelList.as_view(), name="list_panels"),
    path('gene2phenotype/api/panel/<str:name>/', views.PanelDetail.as_view(), name="panel_details"),
    path('gene2phenotype/api/panel/<str:name>/summary/', views.PanelRecordsSummary.as_view(), name="panel_summary"),
    path('gene2phenotype/api/users/', views.UserList.as_view(), name="list_users"),
    path('gene2phenotype/api/attribs/', views.AttribTypeList.as_view(), name="list_attrib_type"),
    path('gene2phenotype/api/attrib/<str:code>/', views.AttribList.as_view(), name="list_attribs_by_type"),
    path('gene2phenotype/api/ontology_terms/variant_types/', views.VariantTypesList.as_view(), name="list_variant_types"),
    path('gene2phenotype/api/gene/<str:name>/', views.LocusGene.as_view(), name="locus_gene"),
    path('gene2phenotype/api/gene/<str:name>/summary/', views.LocusGeneSummary.as_view(), name="locus_gene_summary"),
    path('gene2phenotype/api/gene/<str:name>/function/', views.GeneFunction.as_view(), name="locus_gene_function"),
    path('gene2phenotype/api/gene/<str:name>/disease/', views.GeneDiseaseView.as_view(), name="locus_gene_disease"),
    path('gene2phenotype/api/disease/<str:id>/', views.DiseaseDetail.as_view(), name="disease_details"),
    path('gene2phenotype/api/disease/<str:id>/summary', views.DiseaseSummary.as_view(), name="disease_summary"),
    path('gene2phenotype/api/publication/<str:pmids>/', views.PublicationDetail, name="publication_details"),
    path('gene2phenotype/api/lgd/<str:stable_id>/', views.LocusGenotypeDiseaseDetail.as_view(), name="lgd"),
    path('gene2phenotype/api/search/', views.SearchView.as_view(), name="search"),

    path('gene2phenotype/api/add/disease/', views.AddDisease.as_view(), name="add_disease"),
    path('gene2phenotype/api/add/phenotype/', views.AddPhenotype.as_view(), name="add_phenotype"),
    path('gene2phenotype/api/add/publication/', views.AddPublication.as_view(), name="add_publication"),
    path('gene2phenotype/api/lgd/<str:stable_id>/add_panel/', views.LocusGenotypeDiseaseAddPanel.as_view(), name="lgd_add_panel"),

    ### Curation endpoints ###
    path('gene2phenotype/api/add/curation/', views.AddCurationData.as_view(), name="add_curation_data"),
    path('gene2phenotype/api/curations/', views.ListCurationEntries.as_view(), name="list_curation_entries"),
    path('gene2phenotype/api/curation/<str:stable_id>/', views.CurationDataDetail.as_view(), name="curation_details"),
    path('gene2phenotype/api/curation/<str:stable_id>/update/', views.UpdateCurationData.as_view(), name="update_curation"),

    ### Publish data
    path('gene2phenotype/api/curation/publish/<str:stable_id>/', views.PublishRecord.as_view(), name="publish_record"),
]

urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns += [
    path('api-auth/', include('rest_framework.urls'))
]