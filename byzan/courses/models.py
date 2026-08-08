import uuid

from django.db import models

from accounts.models import User


def generate_certificate_code():
    return uuid.uuid4().hex


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail = models.ImageField(
        upload_to="courses/thumbnails/", blank=True, null=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    instructor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses_instructed",
    )

    def __str__(self):
        return self.title


class Chapter(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="chapters"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=255)
    youtube_url = models.URLField()
    order = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class Transaction(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]
    PROVIDER_CHOICES = [
        ("balance", "Balance"),
        ("midtrans", "Midtrans"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="transactions"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    trx_code = models.CharField(max_length=100, unique=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, default="balance"
    )
    external_id = models.CharField(max_length=100, blank=True, null=True)
    snap_redirect_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.trx_code} - {self.user.email}"


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "course"]  # tidak bisa beli 2x

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"


class LessonProgress(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_progress"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="progress"
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["user", "lesson"]

    def __str__(self):
        return f"{self.user.email} - {self.lesson.title}"


class CourseCertificate(models.Model):
    code = models.CharField(
        max_length=64, unique=True, default=generate_certificate_code
    )
    certificate_number = models.CharField(
        max_length=32, unique=True, blank=True, null=True
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_certificates"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="certificates"
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "course"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.issued_at and not self.certificate_number and self.pk:
            certificate_number = f"BYZ-CRS-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(
                certificate_number=certificate_number
            )
            self.certificate_number = certificate_number

    def __str__(self):
        return f"{self.certificate_number or self.code} - {self.user.email} - {self.course.title}"


class CourseReview(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_reviews"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.course.title} - {self.user.email} - {self.rating}"


class CourseComment(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_comments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="comments"
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.user.email}"


class LessonQuestion(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_questions"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="questions"
    )
    question = models.TextField()
    answer = models.TextField(blank=True)
    answered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_answers",
    )
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lesson.title} - {self.user.email}"
