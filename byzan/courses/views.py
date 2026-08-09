import hashlib
import json
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiExample, extend_schema
from midtransclient import Snap
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from .models import (
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
from .serializers import (
    CourseCertificateSerializer,
    CourseCommentSerializer,
    CourseListSerializer,
    CourseReviewSerializer,
    CourseSerializer,
    LessonAnswerSerializer,
    LessonQuestionSerializer,
    LessonSerializer,
    TransactionSerializer,
)


class CourseListView(APIView):
    @extend_schema(summary="List semua kursus", tags=["Courses"])
    def get(self, request):
        courses = Course.objects.filter(is_published=True).annotate(
            buyers_count=Count("enrollments", distinct=True),
            rating_avg=Avg("reviews__rating"),
            rating_count=Count("reviews", distinct=True),
        )
        serializer = CourseListSerializer(
            courses, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Tambah kursus (admin)", tags=["Courses"], request=CourseSerializer
    )
    def post(self, request):
        if not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CourseSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseDetailView(APIView):
    @extend_schema(summary="Detail kursus + chapters + lessons", tags=["Courses"])
    def get(self, request, pk):
        try:
            course = Course.objects.annotate(
                buyers_count=Count("enrollments", distinct=True),
                rating_avg=Avg("reviews__rating"),
                rating_count=Count("reviews", distinct=True),
            ).get(pk=pk, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        # Cek apakah sudah enroll — kalau belum, sembunyikan youtube_url
        is_enrolled = False
        if request.user and request.user.is_authenticated:
            is_enrolled = Enrollment.objects.filter(
                user=request.user, course=course
            ).exists()

        serializer = CourseSerializer(course, context={"request": request})
        data = serializer.data

        # Kalau belum beli, sembunyikan link video
        can_view_video = (
            (course.price == 0)
            or is_enrolled
            or (
                request.user and request.user.is_authenticated and request.user.is_staff
            )
        )
        if not can_view_video:
            for chapter in data["chapters"]:
                for lesson in chapter["lessons"]:
                    lesson["youtube_url"] = None

        return Response(data)

    @extend_schema(summary="Update kursus (admin)", tags=["Courses"])
    def put(self, request, pk):
        if not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response(
                {"error": "Tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CourseSerializer(
            course, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuyCourseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Beli kursus — buat transaksi + enrollment",
        tags=["Courses"],
        examples=[
            OpenApiExample("Beli kursus", request_only=True, value={"course_id": 1})
        ],
    )
    def post(self, request):
        course_id = request.data.get("course_id")
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        # Cek sudah beli belum
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"error": "Sudah terdaftar di kursus ini"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buat transaksi
        trx = Transaction.objects.create(
            user=request.user,
            course=course,
            amount=course.price,
            status="paid",  # default path bayar langsung (contoh)
            provider="balance",
            trx_code=f"TRX-{uuid.uuid4().hex[:10].upper()}",
            paid_at=timezone.now(),
        )

        # Otomatis enroll setelah bayar
        Enrollment.objects.create(user=request.user, course=course)

        return Response(
            {
                "message": f'Berhasil membeli kursus "{course.title}"',
                "transaction": TransactionSerializer(trx).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MarkLessonDoneView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Tandai lesson selesai",
        tags=["Courses"],
        examples=[
            OpenApiExample("Selesai nonton", request_only=True, value={"lesson_id": 3})
        ],
    )
    def post(self, request):
        lesson_id = request.data.get("lesson_id")
        try:
            lesson = Lesson.objects.get(pk=lesson_id)
        except Lesson.DoesNotExist:
            return Response(
                {"error": "Lesson tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        # Pastikan user sudah enroll kursus ini
        course = lesson.chapter.course
        if (
            (course.price != 0)
            and (not request.user.is_staff)
            and (
                not Enrollment.objects.filter(user=request.user, course=course).exists()
            )
        ):
            return Response(
                {"error": "Kamu belum membeli kursus ini"},
                status=status.HTTP_403_FORBIDDEN,
            )

        progress, created = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save()

        # Hitung total progress kursus
        total = Lesson.objects.filter(chapter__course=course).count()
        done = LessonProgress.objects.filter(
            user=request.user, lesson__chapter__course=course, is_completed=True
        ).count()
        percent = round((done / total) * 100) if total > 0 else 0

        certificate = None
        if total > 0 and percent == 100:
            certificate, created = CourseCertificate.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={"issued_at": timezone.now()},
            )
            if not certificate.issued_at:
                certificate.issued_at = timezone.now()
                certificate.save(update_fields=["issued_at"])

        return Response(
            {
                "message": "Lesson ditandai selesai",
                "lesson_id": lesson.id,
                "progress_percent": percent,
                "course_completed": percent == 100,
                "certificate_issued": certificate is not None
                and certificate.issued_at is not None,
                "certificate_code": certificate.code
                if certificate is not None and certificate.issued_at is not None
                else None,
            }
        )


class BuyCourseWithBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Beli kursus pakai balance",
        tags=["Courses"],
        examples=[
            OpenApiExample(
                "Beli dengan saldo", request_only=True, value={"course_id": 1}
            )
        ],
    )
    def post(self, request):
        course_id = request.data.get("course_id")
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"error": "Sudah terdaftar di kursus ini"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        user.balance = user.balance - course.price
        user.save(update_fields=["balance"])

        trx = Transaction.objects.create(
            user=request.user,
            course=course,
            amount=course.price,
            status="paid",
            provider="balance",
            trx_code=f"TRX-{uuid.uuid4().hex[:10].upper()}",
            paid_at=timezone.now(),
        )

        Enrollment.objects.create(user=request.user, course=course)

        return Response(
            {
                "message": f'Berhasil membeli kursus "{course.title}" dengan saldo',
                "transaction": TransactionSerializer(trx).data,
                "remaining_balance": str(user.balance),
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Helper: dapatkan Midtrans Snap client berdasarkan konfigurasi production/sandbox
# ---------------------------------------------------------------------------
def _get_midtrans_snap() -> Snap:
    if settings.MIDTRANS_IS_PRODUCTION:
        server_key = settings.MIDTRANS_SERVER_KEY
    else:
        server_key = settings.MIDTRANS_SANDBOX_SERVER_KEY
    return Snap(
        is_production=settings.MIDTRANS_IS_PRODUCTION,
        server_key=server_key,
    )


class BuyCourseMidtransInitView(APIView):
    """
    Inisiasi pembelian kursus via Midtrans Snap.

    Flow:
      1. Frontend POST {course_id} ke endpoint ini.
      2. Backend panggil Midtrans Snap API → dapatkan snap_token & redirect_url.
      3. Backend simpan transaksi (status=pending) dan kembalikan redirect_url.
      4. Frontend redirect user ke redirect_url (halaman pembayaran Midtrans).
      5. Setelah user bayar, Midtrans kirim notifikasi ke /api/courses/midtrans/notify/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Inisiasi pembelian via Midtrans Snap",
        description=(
            "Membuat transaksi pending di Midtrans Snap dan mengembalikan `snap_redirect_url` "
            "untuk redirect user ke halaman pembayaran Midtrans. "
            "Setelah user menyelesaikan pembayaran, Midtrans akan mengirim notifikasi ke "
            "`POST /api/courses/midtrans/notify/` untuk konfirmasi dan auto-enroll."
        ),
        tags=["Courses"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "integer",
                        "description": "ID kursus yang ingin dibeli",
                    },
                },
                "required": ["course_id"],
            },
        },
        examples=[
            OpenApiExample(
                "Contoh Request",
                request_only=True,
                value={"course_id": 1},
            ),
            OpenApiExample(
                "Contoh Response (Sukses)",
                response_only=True,
                status_codes=["201"],
                value={
                    "message": "Transaksi dibuat. Selesaikan pembayaran via Midtrans",
                    "transaction": {
                        "id": 15,
                        "trx_code": "MID-A1B2C3D4E5",
                        "course": 1,
                        "course_title": "Belajar Django Pemula",
                        "amount": "150000.00",
                        "status": "pending",
                        "provider": "midtrans",
                        "paid_at": None,
                        "created_at": "2026-08-09T12:30:00+07:00",
                        "snap_redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/abc123...",
                    },
                    "snap_token": "abc123-def456-ghi789",
                    "snap_redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/abc123...",
                },
            ),
            OpenApiExample(
                "Contoh Response (Sudah Terdaftar)",
                response_only=True,
                status_codes=["400"],
                value={"error": "Sudah terdaftar di kursus ini"},
            ),
            OpenApiExample(
                "Contoh Response (Kursus Tidak Ditemukan)",
                response_only=True,
                status_codes=["404"],
                value={"error": "Kursus tidak ditemukan"},
            ),
        ],
    )
    def post(self, request):
        course_id = request.data.get("course_id")
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"error": "Sudah terdaftar di kursus ini"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if course.price == 0:
            return Response(
                {
                    "error": "Kursus ini gratis. Gunakan endpoint POST /api/courses/buy/ untuk langsung enroll.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id = f"MID-{uuid.uuid4().hex[:10].upper()}"

        # --- Panggil Midtrans Snap API untuk dapatkan redirect_url ---
        try:
            snap = _get_midtrans_snap()
            transaction_params = {
                "transaction_details": {
                    "order_id": order_id,
                    "gross_amount": int(course.price),
                },
                "customer_details": {
                    "first_name": request.user.full_name or request.user.username,
                    "email": request.user.email,
                },
                "item_details": [
                    {
                        "id": str(course.id),
                        "price": int(course.price),
                        "quantity": 1,
                        "name": course.title,
                    }
                ],
            }
            snap_response = snap.create_transaction(transaction_params)
            snap_token = snap_response.get("token", "")
            snap_redirect_url = snap_response.get("redirect_url", "")
        except Exception as e:
            logger.exception("Midtrans Snap API error for order %s", order_id)
            return Response(
                {"error": "Gagal membuat transaksi Midtrans. Silakan coba lagi."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        trx = Transaction.objects.create(
            user=request.user,
            course=course,
            amount=course.price,
            status="pending",
            provider="midtrans",
            trx_code=order_id,
            external_id=order_id,
            snap_redirect_url=snap_redirect_url,
        )

        return Response(
            {
                "message": "Transaksi dibuat. Selesaikan pembayaran via Midtrans",
                "transaction": TransactionSerializer(trx).data,
                "snap_token": snap_token,
                "snap_redirect_url": snap_redirect_url,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Midtrans Notification Handler (Webhook)
# ---------------------------------------------------------------------------
@csrf_exempt
def midtrans_notification(request):
    """
    Menerima notifikasi HTTP POST dari Midtrans setelah pembayaran selesai.

    Flow notifikasi:
      1. Midtrans kirim POST JSON (order_id, transaction_status, fraud_status, ...)
      2. Kita validasi signature hash (SHA512: order_id + status_code + gross_amount + server_key)
      3. Update status transaksi di database.
      4. Jika status = settlement/capture → enroll user ke course.
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    order_id = payload.get("order_id", "")
    transaction_status = payload.get("transaction_status", "")
    fraud_status = payload.get("fraud_status", "accept")
    gross_amount = payload.get("gross_amount", "0.00")
    status_code = payload.get("status_code", "200")
    signature_key = payload.get("signature_key", "")

    # --- Validasi signature key ---
    if settings.MIDTRANS_IS_PRODUCTION:
        server_key = settings.MIDTRANS_SERVER_KEY
    else:
        server_key = settings.MIDTRANS_SANDBOX_SERVER_KEY

    raw = order_id + status_code + gross_amount + server_key
    expected_signature = hashlib.sha512(raw.encode()).hexdigest()
    if signature_key != expected_signature:
        logger.warning(
            "Midtrans notification: invalid signature for order %s", order_id
        )
        return HttpResponse("Invalid signature", status=403)

    # --- Cari transaksi berdasarkan external_id (order_id) ---
    try:
        trx = Transaction.objects.get(provider="midtrans", external_id=order_id)
    except Transaction.DoesNotExist:
        logger.warning("Midtrans notification: transaction not found for %s", order_id)
        return HttpResponse("Transaction not found", status=404)

    # --- Mapping status Midtrans → status internal ---
    # Dokumentasi Midtrans:
    #   settlement, capture → paid
    #   pending             → tetap pending
    #   deny, cancel, expire, failure → failed
    #   refund, partial_refund → refunded
    success_statuses = {"settlement", "capture"}
    failure_statuses = {"deny", "cancel", "expire", "failure"}
    refund_statuses = {"refund", "partial_refund"}

    if transaction_status in success_statuses and fraud_status == "accept":
        trx.status = "paid"
        trx.paid_at = timezone.now()
        trx.save(update_fields=["status", "paid_at"])

        # --- Enroll user ke course (jika belum) ---
        Enrollment.objects.get_or_create(user=trx.user, course=trx.course)
        logger.info(
            "Midtrans payment success: order=%s user=%s course=%s",
            order_id, trx.user.email, trx.course.title,
        )

    elif transaction_status in failure_statuses:
        trx.status = "failed"
        trx.save(update_fields=["status"])

    elif transaction_status in refund_statuses:
        trx.status = "refunded"
        trx.save(update_fields=["status"])

    else:
        # pending atau status lain — tidak diubah
        logger.info(
            "Midtrans notification: status=%s for order=%s (no change)",
            transaction_status, order_id,
        )

    return HttpResponse("OK", status=200)


class MyTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Riwayat transaksi saya", tags=["Transactions"])
    def get(self, request):
        trx = Transaction.objects.filter(user=request.user).order_by("-created_at")
        return Response(TransactionSerializer(trx, many=True).data)


class MyCoursesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Kursus yang sudah saya beli", tags=["Courses"])
    def get(self, request):
        enrollments = request.user.enrollments.select_related("course").all()
        courses = [e.course for e in enrollments]
        serializer = CourseListSerializer(
            courses, many=True, context={"request": request}
        )
        return Response(serializer.data)


class MyLessonsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List lesson untuk course yang sudah dibeli",
        tags=["Courses"],
        examples=[
            OpenApiExample(
                "Ambil lesson course", request_only=False, value={"course_id": 1}
            )
        ],
    )
    def get(self, request, course_id=None):
        if course_id is None:
            course_id = request.query_params.get("course_id")
        if not course_id:
            return Response(
                {"error": "course_id wajib"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        is_enrolled = Enrollment.objects.filter(
            user=request.user, course=course
        ).exists()
        can_view_video = (course.price == 0) or is_enrolled or request.user.is_staff
        if not can_view_video:
            return Response(
                {"error": "Kamu belum membeli kursus ini"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CourseSerializer(course, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CourseCertificateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Sertifikat kursus (jika sudah selesai)", tags=["Certificates"]
    )
    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        total = Lesson.objects.filter(chapter__course=course).count()
        done = LessonProgress.objects.filter(
            user=request.user, lesson__chapter__course=course, is_completed=True
        ).count()
        percent = round((done / total) * 100) if total > 0 else 0

        certificate = CourseCertificate.objects.filter(
            user=request.user, course=course, issued_at__isnull=False
        ).first()
        if certificate:
            data = CourseCertificateSerializer(certificate).data
            data["verify_url"] = request.build_absolute_uri(
                f"/api/certificates/{certificate.code}/verify/"
            )
            return Response(
                {"status": "issued", "certificate": data}, status=status.HTTP_200_OK
            )

        return Response(
            {
                "status": "not_issued",
                "total_lessons": total,
                "completed_lessons": done,
                "progress_percent": percent,
                "course_completed": total > 0 and percent == 100,
            },
            status=status.HTTP_200_OK,
        )


class CertificateVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Verifikasi sertifikat by code", tags=["Certificates"])
    def get(self, request, code):
        certificate = (
            CourseCertificate.objects.filter(code=code, issued_at__isnull=False)
            .select_related("user", "course")
            .first()
        )
        if not certificate:
            return Response({"valid": False}, status=status.HTTP_404_NOT_FOUND)

        data = CourseCertificateSerializer(certificate).data
        return Response({"valid": True, "certificate": data}, status=status.HTTP_200_OK)


class CourseReviewListCreateView(APIView):
    @extend_schema(
        summary="List review course",
        tags=["Courses"],
        responses=CourseReviewSerializer(many=True),
    )
    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        reviews = course.reviews.select_related("user").order_by("-created_at")
        return Response(
            CourseReviewSerializer(reviews, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Buat/Update review course (harus sudah beli)",
        tags=["Courses"],
        request=CourseReviewSerializer,
        responses=CourseReviewSerializer,
    )
    def post(self, request, course_id):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": "Login dulu"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        if (
            (course.price != 0)
            and (not request.user.is_staff)
            and (
                not Enrollment.objects.filter(user=request.user, course=course).exists()
            )
        ):
            return Response(
                {"error": "Kamu belum membeli kursus ini"},
                status=status.HTTP_403_FORBIDDEN,
            )

        review = course.reviews.filter(user=request.user).first()
        serializer = CourseReviewSerializer(
            review, data=request.data, partial=review is not None
        )
        if serializer.is_valid():
            obj = serializer.save(user=request.user, course=course)
            return Response(CourseReviewSerializer(obj).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseCommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List komentar course (login)",
        tags=["Courses"],
        responses=CourseCommentSerializer(many=True),
    )
    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        comments = (
            CourseComment.objects.filter(course=course)
            .select_related("user")
            .order_by("-created_at")
        )
        return Response(
            CourseCommentSerializer(comments, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Tambah komentar course (login)",
        tags=["Courses"],
        request=CourseCommentSerializer,
        responses=CourseCommentSerializer,
    )
    def post(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Kursus tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CourseCommentSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save(user=request.user, course=course)
            return Response(
                CourseCommentSerializer(obj).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonQuestionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List Q&A lesson (buyer)",
        tags=["Lessons"],
        responses=LessonQuestionSerializer(many=True),
    )
    def get(self, request, lesson_id):
        try:
            lesson = Lesson.objects.select_related("chapter__course").get(pk=lesson_id)
        except Lesson.DoesNotExist:
            return Response(
                {"error": "Lesson tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        course = lesson.chapter.course
        is_enrolled = Enrollment.objects.filter(
            user=request.user, course=course
        ).exists()
        can_access = (course.price == 0) or is_enrolled or request.user.is_staff
        if not can_access:
            return Response(
                {"error": "Kamu belum membeli kursus ini"},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            LessonQuestion.objects.filter(lesson=lesson)
            .select_related("user", "answered_by")
            .order_by("-created_at")
        )
        return Response(
            LessonQuestionSerializer(qs, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Tanya di lesson (buyer)",
        tags=["Lessons"],
        request=LessonQuestionSerializer,
        responses=LessonQuestionSerializer,
    )
    def post(self, request, lesson_id):
        try:
            lesson = Lesson.objects.select_related("chapter__course").get(pk=lesson_id)
        except Lesson.DoesNotExist:
            return Response(
                {"error": "Lesson tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        course = lesson.chapter.course
        is_enrolled = Enrollment.objects.filter(
            user=request.user, course=course
        ).exists()
        can_access = (course.price == 0) or is_enrolled or request.user.is_staff
        if not can_access:
            return Response(
                {"error": "Kamu belum membeli kursus ini"},
                status=status.HTTP_403_FORBIDDEN,
            )

        question_text = request.data.get("question")
        if not question_text:
            return Response(
                {"question": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj = LessonQuestion.objects.create(
            user=request.user, lesson=lesson, question=question_text
        )
        return Response(
            LessonQuestionSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class LessonQuestionAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Jawab pertanyaan lesson (author/admin)",
        tags=["Lessons"],
        request=LessonAnswerSerializer,
        responses=LessonQuestionSerializer,
    )
    def patch(self, request, question_id):
        question = (
            LessonQuestion.objects.select_related("lesson__chapter__course")
            .filter(pk=question_id)
            .first()
        )
        if not question:
            return Response(
                {"error": "Pertanyaan tidak ditemukan"},
                status=status.HTTP_404_NOT_FOUND,
            )

        course = question.lesson.chapter.course
        is_author = (
            course.instructor_id is not None and course.instructor_id == request.user.id
        )
        if not (request.user.is_staff or is_author):
            return Response(
                {"error": "Hanya pengajar"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = LessonAnswerSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            question.answer = serializer.validated_data.get("answer", "")
            question.answered_by = request.user
            question.answered_at = timezone.now()
            question.save(update_fields=["answer", "answered_by", "answered_at"])
            return Response(
                LessonQuestionSerializer(question).data, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
