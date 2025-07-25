from django.urls import path
from gene2phenotype_app import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def perform_create(self, serializer):
    serializer.save(owner=self.request.user)


# specify URL Path for rest_framework
urlpatterns = [
    path(
        "schema/",
        SpectacularAPIView.as_view(),
        name="schema"
    ),
    path(
        "",
        SpectacularSwaggerView.as_view(
            template_name="swagger-ui.html",
            url_name="schema"
        ),
        name="swagger-ui",
    ),
    path(
        "lgd/<str:stable_id>/",
        views.LocusGenotypeDiseaseDetail.as_view(),
        name="lgd"
    ),
    path("search/",
         views.SearchView.as_view(),
         name="search"
    ),
    path("panels/",
         views.PanelList.as_view(),
         name="list_panels"
    ),
    path("panel/<str:name>/",
         views.PanelDetail.as_view(),
         name="panel_details"
    ),
    path(
        "panel/<str:name>/summary/",
        views.PanelRecordsSummary.as_view(),
        name="panel_summary",
    ),
    path("panel/<str:name>/download/",
         views.PanelDownload,
         name="panel_download"
    ),
    path("user/panels/",
         views.UserPanels.as_view(),
         name="user_panels"
    ),
    path("attribs/",
         views.AttribTypeList.as_view(),
         name="list_attrib_type"
    ),
    path(
        "attribs/description/",
        views.AttribTypeDescriptionList.as_view(),
        name="description_attrib_type",
    ),
    path(
        "attrib/<str:attrib_type>/",
        views.AttribList.as_view(),
        name="list_attribs_by_type",
    ),
    path(
        "molecular_mechanisms/",
        views.ListMolecularMechanisms.as_view(),
        name="list_mechanisms",
    ),
    path(
        "ontology_terms/variant_types/",
        views.VariantTypesList.as_view(),
        name="list_variant_types",
    ),
    path("gene/<str:name>/",
         views.LocusGene.as_view(),
         name="locus_gene"
    ),
    path(
        "gene/<str:name>/summary/",
        views.LocusGeneSummary.as_view(),
        name="locus_gene_summary",
    ),
    path(
        "gene/<str:name>/function/",
        views.GeneFunction.as_view(),
        name="locus_gene_function",
    ),
    path(
        "gene/<str:name>/disease/",
        views.GeneDiseaseView.as_view(),
        name="locus_gene_disease",
    ),

    # Endpoint to update disease cross references
    # It has to be included before the other /disease/ endpoints
    path(
        "disease/<path:name>/cross_references/",
        views.DiseaseUpdateReferences.as_view(),
        name="update_disease_references",
    ),
    path(
        "disease/<path:id>/summary/",
        views.DiseaseSummary.as_view(),
        name="disease_summary",
    ),
    path("disease/<path:id>/",
         views.DiseaseDetail.as_view(),
         name="disease_details"
    ),
    path(
        "publication/<str:pmids>/",
        views.PublicationDetail,
        name="publication_details"
    ),
    path(
        "phenotype/<str:hpo_list>/",
        views.PhenotypeDetail,
        name="phenotype_details"
    ),

    # Endpoint to fetch disease from external sources (OMIM/Mondo)
    path(
        "external_disease/<str:ext_ids>/",
        views.ExternalDisease,
        name="external_disease",
    ),

    ### Endpoints to add data ###
    path(
        "add/disease/",
        views.AddDisease.as_view(),
        name="add_disease"
    ),
    path(
        "add/phenotype/",
        views.AddPhenotype.as_view(),
        name="add_phenotype"
    ),
    path(
        "add/publication/",
        views.AddPublication.as_view(),
        name="add_publication"
    ),

    ### Endpoints to update/add/delete the G2P record (LGD) ###
    path(
        "lgd/<str:stable_id>/update_confidence/",
        views.LGDUpdateConfidence.as_view(),
        name="lgd_update_confidence",
    ),
    # Update molecular mechanism
    # only allows to update if mechanism is "undetermined" and support is "inferred"
    path(
        "lgd/<str:stable_id>/update_mechanism/",
        views.LGDUpdateMechanism.as_view(),
        name="lgd_update_mechanism",
    ),
    # Add or delete panel from LGD record.
    # Actions: PATCH (to delete one panel), POST (to add one panel)
    path(
        "lgd/<str:stable_id>/panel/",
        views.LGDEditPanel.as_view(),
        name="lgd_panel"
    ),
    # Add or delete publication(s) from LGD record.
    # Actions: PATCH (to delete one publication), POST (to add multiple publications)
    path(
        "lgd/<str:stable_id>/publication/",
        views.LGDEditPublications.as_view(),
        name="lgd_publication",
    ),
    # Add or delete phenotype(s) from LGD record.
    # Actions: PATCH (to delete one phenotype), POST (to add multiple phenotypes)
    path(
        "lgd/<str:stable_id>/phenotype/",
        views.LGDEditPhenotypes.as_view(),
        name="lgd_phenotype",
    ),
    # Add or delete a phenotype summary from LGD record.
    # Actions: PATCH (to delete data), POST (to add data)
    path(
        "lgd/<str:stable_id>/phenotype_summary/",
        views.LGDEditPhenotypeSummary.as_view(),
        name="lgd_phenotype_summary",
    ),
    # Add or delete variant consequence(s) from LGD record.
    # Actions: PATCH (to delete one consequence), POST (to add multiple consequences)
    path(
        "lgd/<str:stable_id>/variant_consequence/",
        views.LGDEditVariantConsequences.as_view(),
        name="lgd_var_consequence",
    ),
    # Add or delete cross cutting modifier(s) from LGD record.
    # Actions: PATCH (to delete one ccm), POST (to add multiple ccm)
    path(
        "lgd/<str:stable_id>/cross_cutting_modifier/",
        views.LGDEditCCM.as_view(),
        name="lgd_cross_cutting_modifier",
    ),
    # Add or delete variant type(s) from LGD record.
    # Actions: PATCH (to delete one variant type), POST (to add multiple variant types)
    path(
        "lgd/<str:stable_id>/variant_type/",
        views.LGDEditVariantTypes.as_view(),
        name="lgd_variant_type",
    ),
    # Add or delete variant description(s) from LGD record.
    # Actions: PATCH (to delete one variant description), POST (to add multiple variant descriptions)
    path(
        "lgd/<str:stable_id>/variant_description/",
        views.LGDEditVariantTypeDescriptions.as_view(),
        name="lgd_variant_description",
    ),
    # Add or delete comment(s) from LGD record.
    # Actions: PATCH (to delete comment), POST (to add comment)
    path(
        "lgd/<str:stable_id>/comment/",
        views.LGDEditComment.as_view(),
        name="lgd_comment",
    ),
    # Update the review status of the LGD record. Action: POST
    path(
        "lgd/<str:stable_id>/review/",
        views.LGDEditReview.as_view(),
        name="lgd_review",
    ),
    # Delete LGD record. Action: PATCH
    path(
        "lgd/<str:stable_id>/delete/",
        views.LocusGenotypeDiseaseDelete.as_view(),
        name="lgd_delete",
    ),
    # Update disease IDs for LGD records. Action: POST
    path(
        "lgd_disease_updates/",
        views.LGDUpdateDisease.as_view(),
        name="lgd_disease_updates",
    ),

    ### Endpoints to update other data ###
    # Update disease names in bulk
    path(
        "update/diseases/",
        views.UpdateDisease.as_view(),
        name="update_diseases"
    ),
    # Update ontology terms in bulk
    path(
        "update/disease_ontology_terms/",
        views.UpdateDiseaseOntologyTerms.as_view(),
        name="update_ontology_terms",
    ),

    ### Endpoints to merge or split LGD records ###
    path(
        "merge_records/",
        views.MergeRecords,
        name="merge_records"
    ),

    ### Curation endpoints ###
    path(
        "add/curation/",
        views.AddCurationData.as_view(),
        name="add_curation_data"
    ),
    path(
        "curations/",
        views.ListCurationEntries.as_view(),
        name="list_curation_entries"
    ),
    path(
        "curation/<str:stable_id>/",
        views.CurationDataDetail.as_view(),
        name="curation_details",
    ),
    path(
        "curation/<str:stable_id>/update/",
        views.UpdateCurationData.as_view(),
        name="update_curation",
    ),
    path(
        "curation/<str:stable_id>/delete",
        views.DeleteCurationData.as_view(),
        name="delete_curation",
    ),
    ### Publish data ###
    path(
        "curation/publish/<str:stable_id>/",
        views.PublishRecord.as_view(),
        name="publish_record",
    ),

    ### User management ###
    path(
        "create/user/",
        views.CreateUserView.as_view(),
        name="create_user"
    ),
    path(
        "add_user/panel/",
        views.AddUserToPanelView.as_view(),
        name="add_user_panel"
    ),
    path(
        "profile/",
        views.ManageUserView.as_view(),
        name="profile"
    ),
    path(
        "change_password/",
        views.ChangePasswordView.as_view(),
        name="change_password"
    ),
    path(
        "reset_password/<uid>/<token>/",
        views.ResetPasswordView.as_view(),
        name="reset_password",
    ),
    path(
        "verify/email/",
        views.VerifyEmailView.as_view(),
        name="verify_email"
    ),
    path(
        "login/",
        views.LoginView.as_view(),
        name="_login"
    ),
    path(
        "logout/",
        views.LogOutView.as_view(),
        name="logout"
    ),
    path(
        "token/refresh/",
        views.CustomTokenRefreshView.as_view(),
        name="token_refresh"
    ),

    ### Panels management ###
    path(
        "create/panel/",
        views.PanelCreateView.as_view(),
        name="panel_create"
    ),

    ### Meta information ###
    path(
        "reference_data/",
        views.MetaView.as_view(),
        name="get_reference_data"
    ),

    ### GenCC submission  ###
    path(
        "gencc_create/",
        views.GenCCSubmissionCreateView.as_view(),
        name="create_gencc"
    ),
    path(
        "unsubmitted_stable_ids/",
        views.GenCCSubmissionView.as_view(),
        name="unsubmitted_stable_ids",
    ),
    path(
        "later_review_date/",
        views.StableIDsWithLaterReviewDateView.as_view(),
        name="later_review_date",
    ),
    path(
        "submissions/<str:submission_id>/",
        views.RetrieveStableIDsWithSubmissionID.as_view(),
        name="get_gencc_sub",
    ),
]
