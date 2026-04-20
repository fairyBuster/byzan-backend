from django.urls import path
from .views import (
    PostListView, PostDetailView, PostDetailByIdView,
    AuthorPostListView,
    CategoryListView, AdminPostListView,
    PostCommentListCreateBySlugView, PostCommentListCreateByIdView,
    PostCommentReplyCreateView,
)

urlpatterns = [
    path('',              PostListView.as_view(),    name='post-list'),
    path('admin-all/',    AdminPostListView.as_view(), name='admin-post-list'),
    path('categories/',   CategoryListView.as_view(), name='category-list'),
    path('author/<int:author_id>/', AuthorPostListView.as_view(), name='author-post-list'),
    path('comments/<int:comment_id>/replies/', PostCommentReplyCreateView.as_view(), name='post-comment-reply'),
    path('id/<int:pk>/comments/', PostCommentListCreateByIdView.as_view(), name='post-comments-by-id'),
    path('id/<int:pk>/',  PostDetailByIdView.as_view(), name='post-detail-by-id'),
    path('<slug:slug>/comments/', PostCommentListCreateBySlugView.as_view(), name='post-comments'),
    path('<slug:slug>/',  PostDetailView.as_view(),  name='post-detail'),
]
