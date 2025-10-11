from rest_framework import serializers
from apps.users.models import User, UserProfile
from apps.courses.models import Course, Lesson, Category
from apps.enrollments.models import Enrollment
from apps.comments.models import Comment


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'date_of_birth', 'is_public', 'timezone', 'streak_visibility']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'is_active', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class CourseSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    teacher_id = serializers.IntegerField(write_only=True)
    category_id = serializers.IntegerField(write_only=True)
    lessons_count = serializers.SerializerMethodField()
    enrollments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'main_image', 'created_at',
            'teacher', 'category', 'teacher_id', 'category_id',
            'lessons_count', 'enrollments_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_lessons_count(self, obj):
        return obj.lessons.count()
    
    def get_enrollments_count(self, obj):
        return obj.enrollments.count()


class LessonSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True)
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'content', 'order', 'created_at',
            'course', 'course_id', 'comments_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_comments_count(self, obj):
        return obj.comments.count()


class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)
    course_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'course', 'enrolled_at', 'student_id', 'course_id']
        read_only_fields = ['id', 'enrolled_at']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    lesson = LessonSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    lesson_id = serializers.IntegerField(write_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'text', 'created_at', 'user', 'lesson',
            'user_id', 'lesson_id', 'parent', 'replies'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []
