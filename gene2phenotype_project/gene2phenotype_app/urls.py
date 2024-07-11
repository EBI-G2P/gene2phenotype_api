from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from gene2phenotype_app import views

def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

# specify URL Path for rest_framework
urlpatterns = [
    path('', views.ListEndpoints, name="list_endpoints"),
    path('panels/', views.PanelList.as_view(), name="list_panels"),
    path('panel/<str:name>/', views.PanelDetail.as_view(), name="panel_details"),
    path('panel/<str:name>/summary/', views.PanelRecordsSummary.as_view(), name="panel_summary"),
    path('users/', views.UserList.as_view(), name="list_users"),
    path('attribs/', views.AttribTypeList.as_view(), name="list_attrib_type"),
    path('attrib/<str:code>/', views.AttribList.as_view(), name="list_attribs_by_type"),
    path('molecular_mechanisms/', views.ListMolecularMechanisms.as_view(), name="list_mechanisms"),
    path('ontology_terms/variant_types/', views.VariantTypesList.as_view(), name="list_variant_types"),
    path('gene/<str:name>/', views.LocusGene.as_view(), name="locus_gene"),
    path('gene/<str:name>/summary/', views.LocusGeneSummary.as_view(), name="locus_gene_summary"),
    path('gene/<str:name>/function/', views.GeneFunction.as_view(), name="locus_gene_function"),
    path('gene/<str:name>/disease/', views.GeneDiseaseView.as_view(), name="locus_gene_disease"),
    path('disease/<str:id>/', views.DiseaseDetail.as_view(), name="disease_details"),
    path('disease/<str:id>/summary', views.DiseaseSummary.as_view(), name="disease_summary"),
    path('publication/<str:pmids>/', views.PublicationDetail, name="publication_details"),
    path('phenotype/<str:hpo_list>/', views.PhenotypeDetail, name="phenotype_details"),
    path('lgd/<str:stable_id>/', views.LocusGenotypeDiseaseDetail.as_view(), name="lgd"),
    path('search/', views.SearchView.as_view(), name="search"),

    ### Endpoints to add data ###
    path('add/disease/', views.AddDisease.as_view(), name="add_disease"),
    path('add/phenotype/', views.AddPhenotype.as_view(), name="add_phenotype"),
    path('add/publication/', views.AddPublication.as_view(), name="add_publication"),
    # Add data to the G2P record (LGD)
    path('lgd/<str:stable_id>/add_panel/', views.LocusGenotypeDiseaseAddPanel.as_view(), name="lgd_add_panel"),
    path('lgd/<str:stable_id>/add_publications/', views.LocusGenotypeDiseaseAddPublications.as_view(), name="lgd_add_publications"),
    path('lgd/<str:stable_id>/add_phenotypes/', views.LocusGenotypeDiseaseAddPhenotypes.as_view(), name="lgd_add_phenotypes"),

    ### Curation endpoints ###
    path('add/curation/', views.AddCurationData.as_view(), name="add_curation_data"),
    path('curations/', views.ListCurationEntries.as_view(), name="list_curation_entries"),
    path('curation/<str:stable_id>/', views.CurationDataDetail.as_view(), name="curation_details"),
    path('curation/<str:stable_id>/update/', views.UpdateCurationData.as_view(), name="update_curation"),

    ### Publish data
    path('curation/publish/<str:stable_id>/', views.PublishRecord.as_view(), name="publish_record"),
]

urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns += [
    path('api-auth/', include('rest_framework.urls'))
]