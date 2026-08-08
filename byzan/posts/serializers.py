from accounts.models import User
from rest_framework import serializers

from .models import Category, Post, PostComment, PostCommentReply


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class PostListSerializer(serializers.ModelSerializer):
    """Versi ringkas untuk list — tanpa full content"""

    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    rating_avg = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "thumbnail",
            "thumbnail_url",
            "author",
            "category",
            "status",
            "views_count",
            "created_at",
            "rating_avg",
            "rating_count",
        ]

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if obj.thumbnail and hasattr(obj.thumbnail, "url"):
            url = obj.thumbnail.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_rating_avg(self, obj):
        from django.db.models import Avg

        avg = PostComment.objects.filter(post=obj, rating__isnull=False).aggregate(
            v=Avg("rating")
        )["v"]
        return float(avg) if avg is not None else 0

    def get_rating_count(self, obj):
        return PostComment.objects.filter(post=obj, rating__isnull=False).count()


class PostDetailSerializer(serializers.ModelSerializer):
    """Versi lengkap untuk detail — ada content penuh"""

    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    rating_avg = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "thumbnail",
            "thumbnail_url",
            "author",
            "category",
            "status",
            "views_count",
            "created_at",
            "updated_at",
            "published_at",
            "rating_avg",
            "rating_count",
        ]

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if obj.thumbnail and hasattr(obj.thumbnail, "url"):
            url = obj.thumbnail.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_rating_avg(self, obj):
        from django.db.models import Avg

        avg = PostComment.objects.filter(post=obj, rating__isnull=False).aggregate(
            v=Avg("rating")
        )["v"]
        return float(avg) if avg is not None else 0

    def get_rating_count(self, obj):
        return PostComment.objects.filter(post=obj, rating__isnull=False).count()


class PostWriteSerializer(serializers.ModelSerializer):
    """Untuk create/update oleh admin"""

    class Meta:
        model = Post
        fields = [
            "title",
            "excerpt",
            "content",
            "thumbnail",
            "category",
            "status",
        ]


class PostCommentSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    replies = serializers.SerializerMethodField(read_only=True)
    rating = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "post",
            "user",
            "rating",
            "comment",
            "replies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "post", "user", "created_at", "updated_at"]

    def validate_rating(self, value):
        if value is None:
            return value
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating harus 1 sampai 5")
        return value

    def get_replies(self, obj):
        replies = getattr(obj, "replies", None)
        if replies is None:
            replies = obj.replies.select_related("user").order_by("created_at")
        return PostCommentReplySerializer(replies, many=True).data


class PostCommentReplySerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = PostCommentReply
        fields = ["id", "comment", "user", "message", "created_at"]
        read_only_fields = ["id", "comment", "user", "created_at"]
