from django.contrib import admin
from .models import Post, Category, PostComment, PostCommentReply

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display   = ['title', 'author', 'category', 'status', 'views_count', 'created_at']
    list_editable  = ['status']
    list_filter    = ['status', 'category']
    search_fields  = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views_count', 'created_at', 'updated_at', 'published_at']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "rating", "created_at")
    list_filter = ("rating", "post")
    search_fields = ("post__title", "user__email", "comment")
    ordering = ("-created_at",)


@admin.register(PostCommentReply)
class PostCommentReplyAdmin(admin.ModelAdmin):
    list_display = ("comment", "user", "created_at")
    search_fields = ("comment__post__title", "user__email", "message")
    ordering = ("-created_at",)
