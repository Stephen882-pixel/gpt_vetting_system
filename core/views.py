import os
import re
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse
import google.generativeai as genai
from .models import User, ProgrammingSkill, Question, Response
from .forms import UserRegistrationForm, ProgrammingSkillForm, ResponseForm
import logging
from .utils import generate_questions, evaluate_with_gemini, evaluate_behavioral_response
import speech_recognition as sr
from pydub import AudioSegment

# Set up logging
logger = logging.getLogger('interview')
logging.basicConfig(level=logging.DEBUG)

# Configure Gemini API
genai.configure(api_key='AIzaSyBFfemTtuUdXeSb78B-kpwLBtd9vsTPEyc')  # Replace with your actual key
model = genai.GenerativeModel("gemini-2.0-flash")

# Optionally set FFmpeg path explicitly if needed
# AudioSegment.converter = "/usr/bin/ffmpeg"  # Uncomment and adjust path if FFmpeg isn't in PATH

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    skills = ProgrammingSkill.objects.filter(user=request.user)
    return render(request, 'home.html', {'skills': skills})

@login_required
def skill_create(request):
    if request.method == 'POST':
        form = ProgrammingSkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect('home')
    else:
        form = ProgrammingSkillForm()
    return render(request, 'skill_form.html', {'form': form})

# Generate 6 questions via Gemini API
def generate_questions_via_gemini(skill_language):
    technical_prompt = f"Generate exactly 3 technical coding questions for a {skill_language} interview. Return each question as a separate line."
    behavioral_prompt = "Generate exactly 3 behavioral interview questions. Return each question as a separate line."
    
    try:
        # Fetch technical questions
        technical_response = model.generate_content(technical_prompt)
        logger.info(f"Raw technical response: {technical_response.text}")
        technical_questions = [q.strip() for q in technical_response.text.split('\n') if q.strip()]
        
        # Fetch behavioral questions
        behavioral_response = model.generate_content(behavioral_prompt)
        logger.info(f"Raw behavioral response: {behavioral_response.text}")
        behavioral_questions = [q.strip() for q in behavioral_response.text.split('\n') if q.strip()]
        
        # Ensure exactly 3 questions of each type
        if len(technical_questions) < 3:
            logger.warning(f"Only {len(technical_questions)} technical questions returned. Padding with defaults.")
            technical_questions.extend([f"Default technical question {i+1} for {skill_language}" for i in range(len(technical_questions), 3)])
        elif len(technical_questions) > 3:
            technical_questions = technical_questions[:3]
            
        if len(behavioral_questions) < 3:
            logger.warning(f"Only {len(behavioral_questions)} behavioral questions returned. Padding with defaults.")
            behavioral_questions.extend([f"Default behavioral question {i+1}" for i in range(len(behavioral_questions), 3)])
        elif len(behavioral_questions) > 3:
            behavioral_questions = behavioral_questions[:3]

        return (
            [{'type': 'technical', 'content': q} for q in technical_questions],
            [{'type': 'behavioral', 'content': q} for q in behavioral_questions]
        )
    
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return (
            [{'type': 'technical', 'content': f"Default technical question {i+1} for {skill_language}"} for i in range(3)],
            [{'type': 'behavioral', 'content': f"Default behavioral question {i+1}"} for i in range(3)]
        )

# Evaluate technical response with Gemini
def evaluate_technical_response(question, response_content):
    evaluation_prompt = f"""
    You are an expert technical interviewer evaluating a coding solution.
    Question: {question.content}
    Response: {response_content}
    
    Please provide a comprehensive evaluation with the following details:
    1. Correctness: Does the solution correctly solve the problem?
    2. Efficiency: What is the time and space complexity?
    3. Code Quality: Assess code readability, structure, and best practices
    4. Test Case Coverage: Identify potential edge cases or scenarios not handled
    5. Score: Provide a numerical score out of 100 as a float (e.g., 85.0, not 85/100 or **85**)
    6. Specific, constructive feedback on improvements
    
    Format your response as:
    - Correctness: [Assessment]
    - Efficiency: [Big O analysis]
    - Code Quality: [Evaluation]
    - Test Case Coverage: [Insights]
    - Score: [Float score]
    - Feedback: [Detailed suggestions]
    """
    try:
        response = model.generate_content(evaluation_prompt)
        logger.debug(f"Raw Gemini response for technical evaluation: {response.text}")
        lines = response.text.split('\n')
        score_line = next((line for line in lines if "Score:" in line), "Score: 50.0")
        score_str = score_line.split(':')[1].strip().split()[0] if ':' in score_line else "50.0"
        score_str = score_str.replace('**', '')
        
        try:
            if '/' in score_str:
                numerator = float(score_str.split('/')[0])
                denominator = float(score_str.split('/')[1])
                score = (numerator / denominator) * 100
            else:
                score = float(score_str) if score_str else 50.0
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing score '{score_str}': {str(e)}")
            score = 50.0
        
        feedback = '\n'.join(lines)
        return score, feedback
    except Exception as e:
        logger.error(f"Error in evaluate_technical_response: {str(e)}")
        return 50.0, f"Evaluation failed due to an error: {str(e)}"

# Evaluate behavioral response with Gemini
def evaluate_behavioral_response(video_path, question_content):
    try:
        # Step 1: Verify video file exists
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return 50.0, f"Video file not found: {video_path}"

        # Step 2: Extract audio from video
        logger.debug(f"Processing video file: {video_path}")
        try:
            video = AudioSegment.from_file(video_path)
        except Exception as e:
            logger.error(f"Failed to process video with FFmpeg: {str(e)}")
            return 50.0, f"Video processing failed (FFmpeg error): {str(e)}. Ensure FFmpeg is installed."

        audio_path = video_path.replace('.webm', '.wav')
        logger.debug(f"Exporting audio to: {audio_path}")
        video.export(audio_path, format='wav')

        # Step 3: Convert audio to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            logger.debug("Recording audio from WAV file")
            audio = recognizer.record(source)
            try:
                logger.debug("Attempting speech recognition")
                text = recognizer.recognize_google(audio)
                logger.info(f"Transcribed text: {text}")
            except sr.UnknownValueError:
                logger.warning("Speech recognition failed: No understandable speech detected")
                text = ""
            except sr.RequestError as e:
                logger.error(f"Speech recognition service error: {str(e)}")
                return 50.0, f"Speech recognition service unavailable: {str(e)}"

        # Step 4: Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.debug(f"Cleaned up temporary file: {audio_path}")

        if not text:
            return 40.0, "No speech detected in the video. Please ensure you speak clearly during recording."

        # Step 5: Evaluate with Gemini
        evaluation_prompt = f"""
        You are an expert interviewer evaluating a behavioral interview response.
        
        Transcribed Response:
        {text}
        
        Question: {question_content}
        
        Please provide a comprehensive evaluation:
        1. Communication Clarity
        2. Storytelling Effectiveness
        3. Problem-Solving Demonstration
        4. Professionalism
        5. Relevance to the Question
        
        Provide:
        - Detailed feedback
        - Strengths
        - Areas of improvement
        - Score out of 100 as a float (e.g., 85.0, not 85/100 or **85**). Ensure the score is always provided as a number.
        
        Format your response with clear sections and actionable insights.
        """
        logger.debug("Sending evaluation prompt to Gemini")
        response = model.generate_content(evaluation_prompt)
        logger.debug(f"Full Gemini response for behavioral evaluation: {response.text}")
        
        lines = response.text.split('\n')
        score_line = next((line for line in lines if "Score:" in line), "Score: 50.0")
        score_str = score_line.split(':')[1].strip().split()[0] if ':' in score_line else "50.0"
        score_str = score_str.replace('**', '')

        try:
            if '/' in score_str:
                numerator = float(score_str.split('/')[0])
                denominator = float(score_str.split('/')[1])
                score = (numerator / denominator) * 100
            else:
                score = float(score_str) if score_str else 50.0  # Default to 50.0 if empty
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse score '{score_str}': {str(e)}")
            score = 50.0
        
        feedback = '\n'.join(lines)
        logger.info(f"Evaluated behavioral response - Score: {score}, Feedback: {feedback}")
        return score, feedback

    except Exception as e:
        logger.error(f"Error evaluating behavioral response: {str(e)}")
        return 50.0, f"Unable to evaluate video response due to an error: {str(e)}"

@login_required
def interview(request):
    skills = ProgrammingSkill.objects.filter(user=request.user)
    if not skills:
        request.session['error'] = "Please add a skill before starting an interview."
        return redirect('home')

    # Get or generate exactly 6 questions
    questions = Question.objects.filter(user=request.user)
    if questions.count() != 6:
        Question.objects.filter(user=request.user).delete()
        skill = skills.first()
        technical_qs, behavioral_qs = generate_questions_via_gemini(skill.language)
        if len(technical_qs) != 3 or len(behavioral_qs) != 3:
            logger.error("Gemini API did not return exactly 3 technical and 3 behavioral questions.")
            return render(request, 'interview.html', {'error': 'Error generating questions. Please try again.'})
        
        for q in technical_qs + behavioral_qs:
            Question.objects.create(
                user=request.user,
                type=q['type'],
                content=q['content'],
                skill=skill if q['type'] == 'technical' else None
            )
        questions = Question.objects.filter(user=request.user).order_by('id')[:6]

    total_questions = 6
    answered_questions = Response.objects.filter(question__in=questions).count()
    remaining_questions = total_questions - answered_questions

    if remaining_questions == 0:
        for response in Response.objects.filter(question__in=questions):
            if response.score is None:
                if response.question.type == 'technical':
                    score, feedback = evaluate_technical_response(response.question, response.content)
                else:
                    score, feedback = evaluate_behavioral_response(response.video.path, response.question.content)
                response.score = score
                response.feedback = feedback
                response.save()
        return redirect('interview_results')

    current_question = questions[answered_questions]
    question_type = current_question.type

    if request.method == 'POST':
        if question_type == 'technical':
            content = request.POST.get('content')
            if not content:
                return render(request, 'interview.html', {
                    'error': 'Response cannot be empty.',
                    'question': current_question,
                    'total_questions': total_questions,
                    'remaining_questions': remaining_questions,
                    'current_question': answered_questions + 1,
                })
            Response.objects.create(question=current_question, content=content)
        else:
            video = request.FILES.get('video')
            if not video:
                return render(request, 'interview.html', {
                    'error': 'Video response is required.',
                    'question': current_question,
                    'total_questions': total_questions,
                    'remaining_questions': remaining_questions,
                    'current_question': answered_questions + 1,
                })
            Response.objects.create(question=current_question, video=video)
        return redirect('interview')

    return render(request, 'interview.html', {
        'question': current_question,
        'total_questions': total_questions,
        'remaining_questions': remaining_questions,
        'current_question': answered_questions + 1,
    })

@login_required
def interview_results(request):
    questions = Question.objects.filter(user=request.user).order_by('id')[:6]
    responses = Response.objects.filter(question__in=questions)
    
    technical_responses = responses.filter(question__type='technical')
    behavioral_responses = responses.filter(question__type='behavioral')
    
    total_questions = questions.count()
    average_score = sum(r.score for r in responses if r.score is not None) / responses.count() if responses.exists() else 0
    
    return render(request, 'results.html', {
        'technical_responses': technical_responses,
        'behavioral_responses': behavioral_responses,
        'total_questions': total_questions,
        'average_score': round(average_score, 2),
    })