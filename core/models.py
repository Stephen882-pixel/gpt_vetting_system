from datetime import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
import os

from django.utils import timezone


class User(AbstractUser):
    is_recruiter = models.BooleanField(default=False)

    def __str__(self):
        return self.username

class ProgrammingSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    language = models.CharField(max_length=100)
    proficiency = models.IntegerField()  # Years of experience or proficiency level

    def __str__(self):
        return f"{self.language} ({self.proficiency})"

class Question(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=[('technical', 'Technical'), ('behavioral', 'Behavioral')])
    content = models.TextField()
    skill = models.ForeignKey(ProgrammingSkill, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.content[:50]

class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)  # For technical responses
    video = models.FileField(upload_to='videos/', blank=True, null=True)  # For behavioral responses
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to {self.question}"
    
class Interview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    screen_recording = models.FileField(upload_to='screen_recordings/', blank=True, null=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Interview for {self.user.username} on {self.start_time}"

def screen_recording_path(instance, filename):
    # Save files as: media/screen_recordings/user_<id>/interview_<id>/q<question_number>_<timestamp>.webm
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    ext = os.path.splitext(filename)[1]
    return f'screen_recordings/user_{instance.user.id}/interview_{instance.interview.id}/q{instance.question_number}_{timestamp}{ext}'

class ScreenRecordingChunk(models.Model):
    interview = models.ForeignKey('Interview', on_delete=models.CASCADE, related_name='screen_recording_chunks')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question_number = models.CharField(max_length=10)
    recording = models.FileField(upload_to=screen_recording_path)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Chunk for Interview {self.interview.id}, Question {self.question_number}"
