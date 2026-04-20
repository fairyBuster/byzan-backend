from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="thumbnail",
            field=models.ImageField(blank=True, null=True, upload_to="courses/thumbnails/"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="provider",
            field=models.CharField(choices=[("balance", "Balance"), ("midtrans", "Midtrans")], default="balance", max_length=20),
        ),
        migrations.AddField(
            model_name="transaction",
            name="external_id",
            field=models.CharField(blank=True, null=True, max_length=100),
        ),
        migrations.AddField(
            model_name="transaction",
            name="snap_redirect_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
