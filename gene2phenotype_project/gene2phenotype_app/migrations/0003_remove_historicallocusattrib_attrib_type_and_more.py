# Generated by Django 5.1.5 on 2025-03-18 11:19

import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gene2phenotype_app", "0002_alter_lgdvarianttypecomment_lgd_variant_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="historicallocusattrib",
            name="attrib_type",
        ),
        migrations.RemoveField(
            model_name="historicallocusattrib",
            name="history_user",
        ),
        migrations.RemoveField(
            model_name="historicallocusattrib",
            name="locus",
        ),
        migrations.RemoveField(
            model_name="historicallocusattrib",
            name="source",
        ),
        migrations.RemoveField(
            model_name="historicallocusidentifier",
            name="history_user",
        ),
        migrations.RemoveField(
            model_name="historicallocusidentifier",
            name="locus",
        ),
        migrations.RemoveField(
            model_name="historicallocusidentifier",
            name="source",
        ),
        migrations.AlterField(
            model_name="panel",
            name="description",
            field=models.CharField(default="before_G2P_2025", max_length=255),
        ),
        migrations.CreateModel(
            name="HistoricalLGDComment",
            fields=[
                ("id", models.IntegerField(blank=True, db_index=True)),
                ("comment", models.TextField()),
                ("is_public", models.SmallIntegerField(default=True)),
                ("is_deleted", models.SmallIntegerField(default=False)),
                ("date", models.DateTimeField()),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lgd",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="gene2phenotype_app.locusgenotypedisease",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical lgd comment",
                "verbose_name_plural": "historical lgd comments",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalLGDVariantTypeComment",
            fields=[
                ("id", models.IntegerField(blank=True, db_index=True)),
                ("comment", models.TextField()),
                ("is_public", models.SmallIntegerField(default=True)),
                ("is_deleted", models.SmallIntegerField(default=False)),
                ("date", models.DateTimeField()),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lgd_variant_type",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="gene2phenotype_app.lgdvarianttype",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical lgd variant type comment",
                "verbose_name_plural": "historical lgd variant type comments",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalPublicationComment",
            fields=[
                ("id", models.IntegerField(blank=True, db_index=True)),
                ("comment", models.TextField()),
                ("is_public", models.SmallIntegerField(default=True)),
                ("is_deleted", models.SmallIntegerField(default=False)),
                ("date", models.DateTimeField()),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "publication",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="gene2phenotype_app.publication",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical publication comment",
                "verbose_name_plural": "historical publication comments",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.DeleteModel(
            name="HistoricalLocus",
        ),
        migrations.DeleteModel(
            name="HistoricalLocusAttrib",
        ),
        migrations.DeleteModel(
            name="HistoricalLocusIdentifier",
        ),
    ]
