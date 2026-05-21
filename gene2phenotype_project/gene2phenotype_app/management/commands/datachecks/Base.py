from gene2phenotype_app.models import LGDPanel
from django.db.models import F


def should_process(obj):
    """Return False only for records associated exclusively with the Demo panel."""
    flag = True

    lgd_panels = LGDPanel.objects.filter(lgd_id=obj, is_deleted=0).annotate(
        panel_name=F("panel__name")
    )

    if len(lgd_panels) == 1:
        if lgd_panels[0].panel_name == "Demo":
            flag = False

    return flag
