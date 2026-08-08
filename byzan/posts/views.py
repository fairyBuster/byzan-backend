from accounts.models import User
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Post, PostComment, PostCommentReply
from .serializers import (
    CategorySerializer,
    PostCommentReplySerializer,
    PostCommentSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
)


class PostListView(APIView):
    @extend_schema(
        summary="List semua artikel yang published",
        tags=["Posts"],
        parameters=[
            OpenApiParameter(
                "category", OpenApiTypes.STR, description="Filter by slug kategori"
            ),
            OpenApiParameter("search", OpenApiTypes.STR, description="Cari by judul"),
        ],
        responses=PostListSerializer(many=True),
    )
    def get(self, request):
        posts = Post.objects.filter(status="published").select_related(
            "author", "category"
        )

        # Filter by kategori
        category_slug = request.query_params.get("category")
        if category_slug:
            posts = posts.filter(category__slug=category_slug)

        # Search by judul
        search = request.query_params.get("search")
        if search:
            posts = posts.filter(title__icontains=search)

        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Buat artikel baru (admin)",
        tags=["Posts"],
        request=PostWriteSerializer,
        responses=PostDetailSerializer,
    )
    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": "Login dulu"}, status=status.HTTP_401_UNAUTHORIZED
            )
        if not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostWriteSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.save(author=request.user)

            # Kalau status published, set published_at
            if post.status == "published":
                post.published_at = timezone.now()
                post.save()

            return Response(
                PostDetailSerializer(post).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    def get_object(self, slug):
        try:
            return Post.objects.select_related("author", "category").get(slug=slug)
        except Post.DoesNotExist:
            return None

    @extend_schema(
        summary="Detail artikel by slug", tags=["Posts"], responses=PostDetailSerializer
    )
    def get(self, request, slug):
        post = self.get_object(slug)
        if not post:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        # Draft hanya bisa dilihat admin
        if post.status == "draft":
            if (
                not request.user
                or not request.user.is_authenticated
                or not request.user.is_staff
            ):
                return Response(
                    {"error": "Artikel tidak ditemukan"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Tambah views count setiap kali dibuka
        post.views_count += 1
        post.save(update_fields=["views_count"])

        serializer = PostDetailSerializer(post)
        return Response(serializer.data)

    @extend_schema(
        summary="Update artikel (admin)",
        tags=["Posts"],
        request=PostWriteSerializer,
        responses=PostDetailSerializer,
    )
    def put(self, request, slug):
        if not request.user or not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)

        post = self.get_object(slug)
        if not post:
            return Response(
                {"error": "Tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = PostWriteSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            post = serializer.save()
            if post.status == "published" and not post.published_at:
                post.published_at = timezone.now()
                post.save()
            return Response(PostDetailSerializer(post).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Hapus artikel (admin)", tags=["Posts"])
    def delete(self, request, slug):
        if not request.user or not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)

        post = self.get_object(slug)
        if not post:
            return Response(
                {"error": "Tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        post.delete()
        return Response(
            {"message": "Artikel berhasil dihapus"}, status=status.HTTP_200_OK
        )


class PostDetailByIdView(APIView):
    @extend_schema(
        summary="Detail artikel by id", tags=["Posts"], responses=PostDetailSerializer
    )
    def get(self, request, pk: int):
        try:
            post = Post.objects.select_related("author", "category").get(pk=pk)
        except Post.DoesNotExist:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        if post.status == "draft":
            if (
                not request.user
                or not request.user.is_authenticated
                or not request.user.is_staff
            ):
                return Response(
                    {"error": "Artikel tidak ditemukan"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        post.views_count += 1
        post.save(update_fields=["views_count"])
        return Response(PostDetailSerializer(post).data)


class AuthorPostListView(APIView):
    @extend_schema(
        summary="List artikel published by author",
        tags=["Posts"],
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, description="Cari by judul"),
        ],
        responses=PostListSerializer(many=True),
    )
    def get(self, request, author_id: int):
        try:
            author = User.objects.get(pk=author_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Author tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        posts = Post.objects.filter(status="published", author=author).select_related(
            "author", "category"
        )
        search = request.query_params.get("search")
        if search:
            posts = posts.filter(title__icontains=search)

        data = {
            "author": {
                "id": author.id,
                "username": author.username,
                "full_name": getattr(author, "full_name", "") or "",
            },
            "articles_posted": posts.count(),
            "posts": PostListSerializer(posts, many=True).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    @extend_schema(
        summary="List semua kategori",
        tags=["Posts"],
        responses=CategorySerializer(many=True),
    )
    def get(self, request):
        categories = Category.objects.all()
        return Response(CategorySerializer(categories, many=True).data)

    @extend_schema(
        summary="Tambah kategori (admin)",
        tags=["Posts"],
        request=CategorySerializer,
        responses=CategorySerializer,
    )
    def post(self, request):
        if not request.user or not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminPostListView(APIView):
    """Khusus admin — lihat semua post termasuk draft"""

    @extend_schema(
        summary="Semua artikel termasuk draft (admin)",
        tags=["Posts"],
        responses=PostListSerializer(many=True),
    )
    def get(self, request):
        if not request.user or not request.user.is_staff:
            return Response({"error": "Hanya admin"}, status=status.HTTP_403_FORBIDDEN)
        posts = Post.objects.all().select_related("author", "category")
        return Response(PostListSerializer(posts, many=True).data)


class PostCommentListCreateBySlugView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List komentar & bintang artikel (login)",
        tags=["Posts"],
        responses=PostCommentSerializer(many=True),
    )
    def get(self, request, slug):
        post = (
            Post.objects.filter(slug=slug).select_related("author", "category").first()
        )
        if not post:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )
        if post.status == "draft" and not request.user.is_staff:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        qs = (
            PostComment.objects.filter(post=post)
            .select_related("user")
            .prefetch_related("replies__user")
            .order_by("-created_at")
        )
        return Response(
            PostCommentSerializer(qs, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Tambah/Update komentar & bintang artikel (login)",
        tags=["Posts"],
        request=PostCommentSerializer,
        responses=PostCommentSerializer,
    )
    def post(self, request, slug):
        post = Post.objects.filter(slug=slug).first()
        if not post:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )
        if post.status == "draft" and not request.user.is_staff:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        existing = PostComment.objects.filter(post=post, user=request.user).first()
        serializer = PostCommentSerializer(
            existing, data=request.data, partial=existing is not None
        )
        if serializer.is_valid():
            obj = serializer.save(post=post, user=request.user)
            return Response(PostCommentSerializer(obj).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostCommentListCreateByIdView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List komentar & bintang artikel by id (login)",
        tags=["Posts"],
        responses=PostCommentSerializer(many=True),
    )
    def get(self, request, pk: int):
        post = Post.objects.filter(pk=pk).select_related("author", "category").first()
        if not post:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )
        if post.status == "draft" and not request.user.is_staff:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        qs = (
            PostComment.objects.filter(post=post)
            .select_related("user")
            .prefetch_related("replies__user")
            .order_by("-created_at")
        )
        return Response(
            PostCommentSerializer(qs, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Tambah/Update komentar & bintang artikel by id (login)",
        tags=["Posts"],
        request=PostCommentSerializer,
        responses=PostCommentSerializer,
    )
    def post(self, request, pk: int):
        post = Post.objects.filter(pk=pk).first()
        if not post:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )
        if post.status == "draft" and not request.user.is_staff:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        existing = PostComment.objects.filter(post=post, user=request.user).first()
        serializer = PostCommentSerializer(
            existing, data=request.data, partial=existing is not None
        )
        if serializer.is_valid():
            obj = serializer.save(post=post, user=request.user)
            return Response(PostCommentSerializer(obj).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostCommentReplyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Balas komentar artikel (login)",
        tags=["Posts"],
        request=PostCommentReplySerializer,
        responses=PostCommentReplySerializer,
    )
    def post(self, request, comment_id: int):
        parent = (
            PostComment.objects.select_related("post").filter(pk=comment_id).first()
        )
        if not parent:
            return Response(
                {"error": "Komentar tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        post = parent.post
        if post.status == "draft" and not request.user.is_staff:
            return Response(
                {"error": "Artikel tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = PostCommentReplySerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save(comment=parent, user=request.user)
            return Response(
                PostCommentReplySerializer(obj).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
