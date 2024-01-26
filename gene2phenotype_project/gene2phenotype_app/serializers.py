from rest_framework import serializers
from .models import (Panel, User, UserPanel, AttribType, Attrib,
                     LGDPanel)

class PanelSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)

    class Meta:
        model = Panel
        fields = ['name', 'description']

class PanelDetailSerializer(PanelSerializer):
    curators = serializers.SerializerMethodField()
    number_records = serializers.SerializerMethodField()
    genes = serializers.SerializerMethodField()
    diseases = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()

    def get_curators(self, id):
        x = UserPanel.objects.filter(panel=id)
        users = []
        for u in x:
            if u.user.is_active == 1:
                users.append(u.user.username)
        return users
    
    def get_number_records(self, id):
        x = LGDPanel.objects.filter(panel=id)
        return len(LGDPanelSerializer(x, many=True).data)

    def get_genes(self, id):
        genes = 0
        uniq_genes = {}
        attrib_id = Attrib.objects.get(value='gene').id
        x = LGDPanel.objects.filter(panel=id)
        for lgd_panel in x:
            if lgd_panel.lgd.locus.type.id == attrib_id and lgd_panel.lgd.locus.name not in uniq_genes:
                genes += 1
                uniq_genes = { lgd_panel.lgd.locus.name:1 }
        return genes

    def get_diseases(self, id):
        diseases = 0
        uniq_diseases = {}
        x = LGDPanel.objects.filter(panel=id)
        for lgd_panel in x:
            if lgd_panel.lgd.disease_id not in uniq_diseases:
                diseases += 1
                uniq_diseases = { lgd_panel.lgd.disease_id:1 }
        return diseases

    def get_last_updated(self, id):
        dates = []
        x = LGDPanel.objects.filter(panel=id)
        for lgd_panel in x:
            if lgd_panel.lgd.date_review is not None and lgd_panel.lgd.is_reviewed == 1 and lgd_panel.lgd.is_deleted == 0:
                dates.append(lgd_panel.lgd.date_review)
                dates.sort()
        if len(dates) > 0:
            return dates[-1]
        else:
            return []

    class Meta:
        model = Panel
        fields = PanelSerializer.Meta.fields + ['curators', 'number_records', 'genes', 'diseases', 'last_updated']

class UserSerializer(serializers.ModelSerializer):
    user = serializers.CharField(read_only=True, source="username")
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.CharField(read_only=True)

    def get_panels(self, id):
        x = UserPanel.objects.filter(user=id)
        panels_list = []
        for p in x:
            panels_list.append(p.panel.name)
        return panels_list

    class Meta:
        model = User
        fields = ['user', 'email', 'is_active', 'panels']

class AttribTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttribType
        fields = ['code']

class AttribSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attrib
        fields = ['value']

class LGDPanelSerializer(serializers.ModelSerializer):
    panel = serializers.CharField(source="panel.name")

    class Meta:
        model = LGDPanel
        fields = ['panel']