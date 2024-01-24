from django.db import models
from django.contrib.auth.models import AbstractUser

class Panel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    description = models.CharField(max_length=255, null=True)
    is_visible = models.SmallIntegerField(null=False)

    class Meta:
        db_table = "panel"

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, null=False)
    email = models.CharField(max_length=100, unique=True, null=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateField(null=True)
    is_superuser = models.SmallIntegerField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "user"

class UserPanel(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("User", on_delete=models.PROTECT)
    panel = models.ForeignKey("Panel", on_delete=models.PROTECT)
    is_active = models.SmallIntegerField(null=False)

    class Meta:
        db_table = "user_panel"