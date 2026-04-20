from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0005_coursecertificate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coursecertificate",
            name="certificate_number",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
    ]

