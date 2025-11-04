from django.db import migrations

def assign_default_sponsor(apps, schema_editor):
    Catalogue = apps.get_model('catalogue', 'Catalogue')
    SponsorProfile = apps.get_model('users', 'SponsorProfile')

    default_sponsor = SponsorProfile.objects.first()  # safest: first sponsor
    if not default_sponsor:
        # If no sponsors exist yet, just skip assigning for now
        return

    for catalogue in Catalogue.objects.filter(sponsor__isnull=True):
        catalogue.sponsor = default_sponsor
        catalogue.save(update_fields=['sponsor'])

class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0009_alter_catalogue_sponsor'),  # replace with your last migration
        ('users', '0012_driversponsor'),    # replace with your last users migration
    ]

    operations = [
        migrations.RunPython(assign_default_sponsor),
    ]
