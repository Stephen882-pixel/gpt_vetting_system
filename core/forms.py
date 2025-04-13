from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ProgrammingSkill, Response

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    is_recruiter = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'is_recruiter']

class ProgrammingSkillForm(forms.ModelForm):
    class Meta:
        model = ProgrammingSkill
        fields = ['language', 'proficiency']

class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'rows': 5})}


