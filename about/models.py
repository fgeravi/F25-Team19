from django.db import models

class About(models.Model):
    idabout = models.AutoField(primary_key=True)
    team_num = models.IntegerField()
    version_number = models.IntegerField()
    release_date = models.DateField(null=True, blank=True)
    product_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'about'
        managed = False
