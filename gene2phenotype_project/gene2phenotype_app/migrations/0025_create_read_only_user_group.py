from django.db import migrations


def create_read_only_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.using(schema_editor.connection.alias).get_or_create(name="read_only")


class Migration(migrations.Migration):

    dependencies = [
        (
            "gene2phenotype_app",
            "0024_alter_lgdmolecularmechanismsynopsis_unique_together_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(create_read_only_group),
    ]
