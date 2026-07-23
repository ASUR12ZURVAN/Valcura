from django.db import models


class UserRequest(models.Model):
    ph_number = models.IntegerField()

    Language = models.CharField( max_length= 200)
    Service_Type = models.CharField(max_length=200)

    
