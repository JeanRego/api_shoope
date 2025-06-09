from django.db import models

class ShopeeConta(models.Model):
    nome = models.CharField(max_length=100)
    partner_id = models.BigIntegerField()
    shop_id = models.BigIntegerField()
    partner_key = models.CharField(max_length=255)
    access_token = models.CharField(max_length=255)
