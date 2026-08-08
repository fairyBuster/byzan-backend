import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import courses.models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0004_alter_chapter_options_alter_lesson_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseCertificate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        default=courses.models.generate_certificate_code,
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "certificate_number",
                    models.CharField(blank=True, max_length=32, unique=True),
                ),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificates",
                        to="courses.course",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_certificates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "course")},
            },
        ),
    ]
