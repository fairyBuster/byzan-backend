from django.urls import path

from .views import (
    BuyCourseMidtransInitView,
    BuyCourseView,
    BuyCourseWithBalanceView,
    CourseCertificateView,
    CourseCommentListCreateView,
    CourseDetailView,
    CourseListView,
    CourseReviewListCreateView,
    LessonQuestionAnswerView,
    LessonQuestionListCreateView,
    MarkLessonDoneView,
    MyCoursesView,
    MyLessonsView,
    MyTransactionView,
    midtrans_notification,
)

urlpatterns = [
    path("", CourseListView.as_view(), name="course-list"),
    path(
        "<int:course_id>/reviews/",
        CourseReviewListCreateView.as_view(),
        name="course-reviews",
    ),
    path(
        "<int:course_id>/comments/",
        CourseCommentListCreateView.as_view(),
        name="course-comments",
    ),
    path(
        "<int:course_id>/certificate/",
        CourseCertificateView.as_view(),
        name="course-certificate",
    ),
    path("<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("buy/", BuyCourseView.as_view(), name="buy-course"),
    path("buy/balance/", BuyCourseWithBalanceView.as_view(), name="buy-balance"),
    path("buy/midtrans/", BuyCourseMidtransInitView.as_view(), name="buy-midtrans"),
    path("midtrans/notify/", midtrans_notification, name="midtrans-notify"),
    path("lesson/complete/", MarkLessonDoneView.as_view(), name="lesson-complete"),
    path(
        "lessons/<int:lesson_id>/questions/",
        LessonQuestionListCreateView.as_view(),
        name="lesson-questions",
    ),
    path(
        "lessons/questions/<int:question_id>/answer/",
        LessonQuestionAnswerView.as_view(),
        name="lesson-question-answer",
    ),
    path("my/", MyCoursesView.as_view(), name="my-courses"),
    path("my/lessons/", MyLessonsView.as_view(), name="my-lessons"),
    path(
        "my/lessons/<int:course_id>/",
        MyLessonsView.as_view(),
        name="my-lessons-by-course",
    ),
    path("transactions/", MyTransactionView.as_view(), name="my-transactions"),
]
