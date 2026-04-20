from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_address_user_balance_user_city_user_country_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gender",
            field=models.CharField(blank=True, choices=[("male", "Male"), ("female", "Female")], max_length=10),
        ),
        migrations.AddField(
            model_name="user",
            name="birthday",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="instagram_link",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="facebook_link",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
    ]

