from django.contrib import admin

from .models import (
    Chapter,
    Course,
    CourseCertificate,
    CourseComment,
    CourseReview,
    Enrollment,
    Lesson,
    LessonProgress,
    LessonQuestion,
    Transaction,
)


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ("title", "order")
    ordering = ("order",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "is_published", "price", "created_at")
    list_filter = ("is_published", "instructor")
    search_fields = ("title", "instructor__username", "instructor__email")
    ordering = ("-created_at",)
    inlines = [ChapterInline]
    fields = (
        "title",
        "description",
        "thumbnail",
        "price",
        "is_published",
        "instructor",
    )


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ("title", "youtube_url", "order", "duration_seconds")
    ordering = ("order",)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    ordering = ("course", "order")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "chapter", "order", "duration_seconds")
    list_filter = ("chapter__course", "chapter")
    search_fields = ("title", "chapter__title", "chapter__course__title")
    ordering = ("chapter", "order")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "trx_code",
        "user",
        "course",
        "amount",
        "status",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "course")
    search_fields = ("trx_code", "user__email", "course__title")
    ordering = ("-created_at",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at")
    list_filter = ("course",)
    search_fields = ("user__email", "course__title")
    ordering = ("-enrolled_at",)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "is_completed", "completed_at")
    list_filter = ("is_completed",)
    search_fields = ("user__email", "lesson__title", "lesson__chapter__course__title")
    ordering = ("-completed_at",)


@admin.register(CourseCertificate)
class CourseCertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_number", "user", "course", "issued_at", "created_at")
    list_filter = ("course",)
    search_fields = ("certificate_number", "code", "user__email", "course__title")
    ordering = ("-created_at",)


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "rating", "created_at")
    list_filter = ("rating", "course")
    search_fields = ("course__title", "user__email", "comment")
    ordering = ("-created_at",)


@admin.register(CourseComment)
class CourseCommentAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "created_at")
    list_filter = ("course",)
    search_fields = ("course__title", "user__email", "comment")
    ordering = ("-created_at",)


@admin.register(LessonQuestion)
class LessonQuestionAdmin(admin.ModelAdmin):
    list_display = ("lesson", "user", "answered_by", "answered_at", "created_at")
    list_filter = ("lesson__chapter__course", "answered_at")
    search_fields = ("lesson__title", "user__email", "question", "answer")
    ordering = ("-created_at",)
