from rest_framework import serializers
from .models import Course, Chapter, Lesson, Transaction, Enrollment, LessonProgress, CourseCertificate, CourseReview, CourseComment, LessonQuestion


class LessonSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model  = Lesson
        fields = ['id', 'title', 'youtube_url', 'order', 'duration_seconds', 'is_completed']

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return LessonProgress.objects.filter(
            user=request.user, lesson=obj, is_completed=True
        ).exists()


class ChapterSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model  = Chapter
        fields = ['id', 'title', 'order', 'lessons']


class CourseSerializer(serializers.ModelSerializer):
    chapters         = ChapterSerializer(many=True, read_only=True)
    total_lessons    = serializers.SerializerMethodField()
    is_enrolled      = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    thumbnail_url    = serializers.SerializerMethodField(read_only=True)
    instructor       = serializers.SerializerMethodField(read_only=True)
    buyers_count     = serializers.SerializerMethodField()
    rating_avg       = serializers.SerializerMethodField()
    rating_count     = serializers.SerializerMethodField()

    class Meta:
        model  = Course
        fields = [
            'id', 'title', 'description', 'thumbnail', 'thumbnail_url', 'price',
            'is_published', 'created_at', 'chapters',
            'total_lessons', 'is_enrolled', 'progress_percent',
            'instructor',
            'buyers_count', 'rating_avg', 'rating_count',
        ]

    def get_total_lessons(self, obj):
        return Lesson.objects.filter(chapter__course=obj).count()

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Enrollment.objects.filter(user=request.user, course=obj).exists()

    def get_progress_percent(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        total = Lesson.objects.filter(chapter__course=obj).count()
        if total == 0:
            return 0
        done = LessonProgress.objects.filter(
            user=request.user,
            lesson__chapter__course=obj,
            is_completed=True
        ).count()
        return round((done / total) * 100)
    
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            url = obj.thumbnail.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None
    
    def get_instructor(self, obj):
        if obj.instructor:
            return {
                'id': obj.instructor.id,
                'username': obj.instructor.username,
                'full_name': getattr(obj.instructor, 'full_name', '') or '',
                'email': obj.instructor.email
            }
        return None
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data.setdefault('instructor', request.user)
        return super().create(validated_data)
    
    def get_buyers_count(self, obj):
        value = getattr(obj, 'buyers_count', None)
        if value is not None:
            return value
        return Enrollment.objects.filter(course=obj).count()

    def get_rating_avg(self, obj):
        value = getattr(obj, 'rating_avg', None)
        if value is not None:
            return float(value) if value is not None else 0
        from django.db.models import Avg
        avg = CourseReview.objects.filter(course=obj).aggregate(v=Avg('rating'))['v']
        return float(avg) if avg is not None else 0

    def get_rating_count(self, obj):
        value = getattr(obj, 'rating_count', None)
        if value is not None:
            return value
        return CourseReview.objects.filter(course=obj).count()


class CourseListSerializer(serializers.ModelSerializer):
    """Versi ringkas untuk list — tanpa detail chapter"""
    total_lessons = serializers.SerializerMethodField()
    completed_lessons = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    is_enrolled   = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    instructor_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    buyers_count = serializers.SerializerMethodField()
    rating_avg = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model  = Course
        fields = [
            'id',
            'title',
            'thumbnail',
            'thumbnail_url',
            'price',
            'created_at',
            'total_lessons',
            'completed_lessons',
            'progress_percent',
            'buyers_count',
            'rating_avg',
            'rating_count',
            'is_enrolled',
            'instructor_name',
        ]

    def get_total_lessons(self, obj):
        return Lesson.objects.filter(chapter__course=obj).count()

    def get_completed_lessons(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return LessonProgress.objects.filter(
            user=request.user,
            lesson__chapter__course=obj,
            is_completed=True
        ).count()

    def get_progress_percent(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        total = self.get_total_lessons(obj)
        if total == 0:
            return 0
        done = self.get_completed_lessons(obj)
        return round((done / total) * 100)

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Enrollment.objects.filter(user=request.user, course=obj).exists()
    
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            url = obj.thumbnail.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None
    
    def get_instructor_name(self, obj):
        if obj.instructor:
            return getattr(obj.instructor, 'full_name', '') or obj.instructor.username
        return None
    
    def get_buyers_count(self, obj):
        value = getattr(obj, 'buyers_count', None)
        if value is not None:
            return value
        return Enrollment.objects.filter(course=obj).count()

    def get_rating_avg(self, obj):
        value = getattr(obj, 'rating_avg', None)
        if value is not None:
            return float(value) if value is not None else 0
        from django.db.models import Avg
        avg = CourseReview.objects.filter(course=obj).aggregate(v=Avg('rating'))['v']
        return float(avg) if avg is not None else 0

    def get_rating_count(self, obj):
        value = getattr(obj, 'rating_count', None)
        if value is not None:
            return value
        return CourseReview.objects.filter(course=obj).count()


class TransactionSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model  = Transaction
        fields = ['id', 'trx_code', 'course', 'course_title', 'amount', 'status', 'provider', 'paid_at', 'created_at', 'snap_redirect_url']
        read_only_fields = ['trx_code', 'amount', 'status', 'provider', 'paid_at', 'created_at', 'snap_redirect_url']


class CourseCertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = CourseCertificate
        fields = [
            'id',
            'code',
            'certificate_number',
            'issued_at',
            'created_at',
            'course',
            'course_title',
            'user',
            'user_email',
            'user_full_name',
        ]
        read_only_fields = fields


class CourseReviewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseReview
        fields = ['id', 'course', 'user', 'rating', 'created_at', 'updated_at']
        read_only_fields = ['id', 'course', 'user', 'created_at', 'updated_at']

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': getattr(obj.user, 'full_name', '') or '',
        }

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating harus 1 sampai 5')
        return value


class CourseCommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseComment
        fields = ['id', 'course', 'user', 'comment', 'created_at']
        read_only_fields = ['id', 'course', 'user', 'created_at']

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': getattr(obj.user, 'full_name', '') or '',
        }


class LessonQuestionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)
    answered_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LessonQuestion
        fields = ['id', 'lesson', 'user', 'question', 'answer', 'answered_by', 'answered_at', 'created_at']
        read_only_fields = ['id', 'lesson', 'user', 'answer', 'answered_by', 'answered_at', 'created_at']

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': getattr(obj.user, 'full_name', '') or '',
        }

    def get_answered_by(self, obj):
        if obj.answered_by:
            return {
                'id': obj.answered_by.id,
                'username': obj.answered_by.username,
                'full_name': getattr(obj.answered_by, 'full_name', '') or '',
            }
        return None


class LessonAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonQuestion
        fields = ['answer']
