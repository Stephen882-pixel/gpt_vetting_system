from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ProgrammingSkill, Question, Response

# Custom User Admin to handle your custom User model
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_recruiter', 'is_staff', 'date_joined')
    list_filter = ('is_recruiter', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('username',)

    # Define fields for add/edit forms
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email',)}),
        ('Permissions', {'fields': ('is_recruiter', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_recruiter'),
        }),
    )

@admin.register(ProgrammingSkill)
class ProgrammingSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'proficiency')
    list_filter = ('language',)
    search_fields = ('user__username', 'language')
    ordering = ('user',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('content_short', 'user', 'type', 'skill')
    list_filter = ('type', 'skill__language')
    search_fields = ('content', 'user__username')
    ordering = ('user',)

    def content_short(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Question'

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'content_short', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('question__content', 'content')
    ordering = ('-created_at',)

    def question_short(self, obj):
        return obj.question.content[:50] + '...' if len(obj.question.content) > 50 else obj.question.content
    question_short.short_description = 'Question'

    def content_short(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Response'

# If you want to unregister the default User model (optional)
# from django.contrib.auth.models import User as DefaultUser
# admin.site.unregister(DefaultUser)