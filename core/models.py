from django.db import models
from django.contrib.auth.models import AbstractUser

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