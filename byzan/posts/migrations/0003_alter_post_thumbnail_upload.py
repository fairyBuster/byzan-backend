from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0002_seed_religion_categories_posts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="thumbnail",
            field=models.ImageField(blank=True, null=True, upload_to="posts/thumbnails/"),
        ),
    ]

