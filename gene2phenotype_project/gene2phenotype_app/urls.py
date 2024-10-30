from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.authtoken import views as authviews
from gene2phenotype_app import views
from knox import views as knox_views

def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

# specify URL Path for rest_framework
urlpatterns = [
    path('', views.ListEndpoints, name="list_endpoints"),
    path('panels/', views.PanelList.as_view(), name="list_panels"),
    path('panel/<str:name>/', views.PanelDetail.as_view(), name="panel_details"),
    path('panel/<str:name>/summary/', views.PanelRecordsSummary.as_view(), name="panel_summary"),
    path('panel/<str:name>/download/', views.PanelDownload, name="panel_download"),
    path('users/', views.UserList.as_view(), name="list_users"),
    path('user/panels/', views.UserPanels.as_view(), name="user_panels"),
    path('attribs/', views.AttribTypeList.as_view(), name="list_attrib_type"),
    path('attribs/description', views.AttribTypeDescriptionList.as_view(), name="description_attrib_type"),
    path('attrib/<str:code>/', views.AttribList.as_view(), name="list_attribs_by_type"),
    path('molecular_mechanisms/', views.ListMolecularMechanisms.as_view(), name="list_mechanisms"),
    path('ontology_terms/variant_types/', views.VariantTypesList.as_view(), name="list_variant_types"),
    path('gene/<str:name>/', views.LocusGene.as_view(), name="locus_gene"),
    path('gene/<str:name>/summary/', views.LocusGeneSummary.as_view(), name="locus_gene_summary"),
    path('gene/<str:name>/function/', views.GeneFunction.as_view(), name="locus_gene_function"),
    path('gene/<str:name>/disease/', views.GeneDiseaseView.as_view(), name="locus_gene_disease"),
    path('disease/<path:id>/summary/', views.DiseaseSummary.as_view(), name="disease_summary"),
    path('disease/<path:id>/', views.DiseaseDetail.as_view(), name="disease_details"),
    path('publication/<str:pmids>/', views.PublicationDetail, name="publication_details"),
    path('phenotype/<str:hpo_list>/', views.PhenotypeDetail, name="phenotype_details"),
    path('lgd/<str:stable_id>/', views.LocusGenotypeDiseaseDetail.as_view(), name="lgd"),
    path('search/', views.SearchView.as_view(), name="search"),

    ### Endpoints to add data ###
    path('add/disease/', views.AddDisease.as_view(), name="add_disease"),
    path('add/phenotype/', views.AddPhenotype.as_view(), name="add_phenotype"),
    path('add/publication/', views.AddPublication.as_view(), name="add_publication"),

    ### Endpoints to update/add/delete the G2P record (LGD) ###
    path('lgd/<str:stable_id>/update_confidence/', views.LGDUpdateConfidence.as_view(), name="lgd_update_confidence"),
    # Update molecular mechanism - only allows to update if mechanism is 'undetermined' and support is 'inferred'
    path('lgd/<str:stable_id>/update_mechanism/', views.LGDUpdateMechanism.as_view(), name="lgd_update_mechanism"),
    # Add or delete panel from LGD record. Actions: UPDATE (to delete one panel), POST (to add one panel)
    path('lgd/<str:stable_id>/panel/', views.LGDEditPanel.as_view(), name="lgd_panel"),
    # Add or delete publication(s) from LGD record. Actions: UPDATE (to delete one publication), POST (to add multiple publications)
    path('lgd/<str:stable_id>/publication/', views.LGDEditPublications.as_view(), name="lgd_publication"),
    # Add or delete phenotype(s) from LGD record. Actions: UPDATE (to delete one phenotype), POST (to add multiple phenotypes)
    path('lgd/<str:stable_id>/phenotype/', views.LGDEditPhenotypes.as_view(), name="lgd_phenotype"),
    # Add or delete a phenotype summary from LGD record. Actions: UPDATE (to delete data), POST (to add data)
    path('lgd/<str:stable_id>/phenotype_summary/', views.LGDEditPhenotypeSummary.as_view(), name="lgd_phenotype_summary"),
    # Add or delete variant consequence(s) from LGD record. Actions: UPDATE (to delete one consequence), POST (to add multiple consequences)
    path('lgd/<str:stable_id>/variant_consequence/', views.LGDEditVariantConsequences.as_view(), name="lgd_var_consequence"),
    # Add or delete cross cutting modifier(s) from LGD record. Actions: UPDATE (to delete one ccm), POST (to add multiple ccm)
    path('lgd/<str:stable_id>/cross_cutting_modifier/', views.LGDEditCCM.as_view(), name="lgd_cross_cutting_modifier"),
    # Add or delete variant type(s) from LGD record. Actions: UPDATE (to delete one variant type), POST (to add multiple variant types)
    path('lgd/<str:stable_id>/variant_type/', views.LGDEditVariantTypes.as_view(), name="lgd_variant_type"),
    # Add or delete variant description(s) from LGD record. Actions: UPDATE (to delete one variant description), POST (to add multiple variant descriptions)
    path('lgd/<str:stable_id>/variant_description/', views.LGDEditVariantTypeDescriptions.as_view(), name="lgd_variant_description"),
    # Add or delete comment from LGD record. Actions: UPDATE (to delete comment), POST (to add comment)
    path('lgd/<str:stable_id>/comment/', views.LGDEditComment.as_view(), name="lgd_comment"),
    # Delete LGD record. Action: UPDATE
    path('lgd/<str:stable_id>/delete/', views.LocusGenotypeDiseaseDelete.as_view(), name="lgd_delete"),

    ### Curation endpoints ###
    path('add/curation/', views.AddCurationData.as_view(), name="add_curation_data"),
    path('curations/', views.ListCurationEntries.as_view(), name="list_curation_entries"),
    path('curation/<str:stable_id>/', views.CurationDataDetail.as_view(), name="curation_details"),
    path('curation/<str:stable_id>/update/', views.UpdateCurationData.as_view(), name="update_curation"),
    path('curation/<str:stable_id>/delete', views.DeleteCurationData.as_view(), name="delete_curation"),

    ### Publish data
    path('curation/publish/<str:stable_id>/', views.PublishRecord.as_view(), name="publish_record"),

    #user management
    path("create/user/", views.CreateUserView.as_view(), name="create"),
    path('profile/', views.ManageUserView.as_view(), name='profile'),
    path('login/', views.LoginView.as_view(), name='knox_login'),
    path('logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),

]

urlpatterns = format_suffix_patterns(urlpatterns)