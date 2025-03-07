import json
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from gene2phenotype_app.models import Attrib, AttribType

class AttribTypeListTestEndpoint(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/attribs.json"]
    def setUp(self):
        self.url_attribtypelist = reverse("list_attrib_type")

    
    def test_attrib_type_list(self):
        response = self.client.get(self.url_attribtypelist)

        self.assertEqual(response.status_code, 200)
        self.assertIn("confidence_category", response.data)


class AttribListTestEndpoint(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/attribs.json"]
    def setUp(self):

        self.url_attriblist = reverse("list_attribs_by_type", kwargs={"code": "confidence_category"})
        
    
    def test_attrib_list_code(self):
        response = self.client.get(self.url_attriblist)


        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 6)
        