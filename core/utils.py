import os
import speech_recognition as sr
from pydub import AudioSegment
from textblob import TextBlob
import logging

logger = logging.getLogger(__name__)

# Mock Gemini question generation (replace with actual Gemini API)
def generate_questions(skill, question_type, count):
    if question_type == 'technical':
        return [
            {'type': 'technical', 'content': "Given two sorted arrays of integers, write a Java function to merge them into a single sorted array without using built-in sorting functions."},
            {'type': 'technical', 'content': "Write a Python function to reverse a linked list."},
            {'type': 'technical', 'content': "Implement a binary search algorithm in JavaScript."},
        ][:count]
    else:
        return [
            {'type': 'behavioral', 'content': "Tell me about a time when you had to work with a difficult team member. How did you handle it?"},
            {'type': 'behavioral', 'content': "Describe a situation where you failed at a task. What did you learn from it?"},
            {'type': 'behavioral', 'content': "How do you manage stress during a high-pressure project?"},
        ][:count]

# Mock Gemini evaluation for technical responses (replace with actual Gemini API)
def evaluate_with_gemini(question, response_content):
    if "mergeSortedArrays" in question.content:
        expected = "The code should implement a merge function for two sorted arrays."
        if "mergeSortedArrays" in response_content:
            return 75.0, "Good implementation, but consider edge cases like empty arrays."
        else:
            return 40.0, "Incorrect implementation. Missing merge logic."
    return 50.0, "Average response. Needs more detail."

# Evaluate behavioral response by analyzing video
def evaluate_behavioral_response(video_path):
    try:
        # Step 1: Extract audio from video
        video = AudioSegment.from_file(video_path)
        audio_path = video_path.replace('.webm', '.wav')
        video.export(audio_path, format='wav')

        # Step 2: Convert audio to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                text = ""
                logger.warning("Speech recognition could not understand the audio.")
            except sr.RequestError as e:
                logger.error(f"Speech recognition error: {str(e)}")
                return 50.0, "Unable to process audio due to a recognition error."

        # Clean up temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # Step 3: Analyze the text
        if not text:
            return 40.0, "No speech detected in the video. Please speak clearly and try again."

        # Sentiment analysis using TextBlob
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity  # Ranges from -1 (negative) to 1 (positive)
        sentiment_score = (sentiment + 1) * 50  # Normalize to 0-100

        # Clarity analysis (simple heuristic)
        word_count = len(text.split())
        filler_words = ['um', 'uh', 'like', 'you know']
        filler_count = sum(text.lower().count(filler) for filler in filler_words)
        filler_ratio = filler_count / word_count if word_count > 0 else 0
        clarity_score = max(50, 100 - (filler_ratio * 100))  # Penalize for excessive fillers

        # Combine scores (weighted average)
        final_score = (sentiment_score * 0.6) + (clarity_score * 0.4)
        final_score = min(max(final_score, 0), 100)  # Clamp between 0 and 100

        # Generate feedback
        feedback = f"Transcribed Response: '{text}'. "
        feedback += f"Sentiment Score: {sentiment_score:.2f}% (Positive sentiment indicates confidence). "
        feedback += f"Clarity Score: {clarity_score:.2f}% (Based on filler word usage). "
        if final_score > 80:
            feedback += "Great response! You spoke clearly and with confidence."
        elif final_score > 60:
            feedback += "Good response, but try to reduce filler words (e.g., 'um', 'like') to sound more confident."
        else:
            feedback += "Your response could be improved. Speak more clearly and avoid filler words to enhance clarity and confidence."

        return final_score, feedback

    except Exception as e:
        logger.error(f"Error evaluating behavioral response: {str(e)}")
        return 50.0, "Unable to evaluate video response due to an error."