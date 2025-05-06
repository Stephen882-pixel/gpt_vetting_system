import os
import re
import traceback
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

def evaluate_behavioral_response(video_path, question_content):
    """
    A robust behavioral response evaluator that combines:
    1. Better speech recognition
    2. Fallback to TextBlob analysis if Gemini API fails
    3. Improved score extraction
    4. Detailed logging for debugging
    """
    try:
        # Step 1: Verify video file exists
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return 50.0, f"Video file not found: {video_path}"

        # Step 2: Extract audio from video with better error handling
        logger.debug(f"Processing video file: {video_path}")
        try:
            video = AudioSegment.from_file(video_path)
        except Exception as e:
            logger.error(f"Failed to process video with FFmpeg: {str(e)}")
            return 50.0, f"Video processing failed (FFmpeg error): {str(e)}. Ensure FFmpeg is installed."

        audio_path = video_path.replace('.webm', '.wav')
        logger.debug(f"Exporting audio to: {audio_path}")
        video.export(audio_path, format='wav')

        # Step 3: Convert audio to text with improved recognition
        transcribed_text = transcribe_audio(audio_path)
        
        # Clean up temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.debug(f"Cleaned up temporary file: {audio_path}")

        if not transcribed_text:
            return 40.0, "No speech detected in the video. Please ensure you speak clearly during recording."
            
        logger.info(f"Successfully transcribed response: '{transcribed_text[:100]}...' ({len(transcribed_text)} chars)")

        # Step 4: Try evaluating with Gemini API first
        try:
            gemini_score, gemini_feedback = evaluate_with_gemini_api(question_content, transcribed_text)
            logger.info(f"Gemini evaluation successful - Score: {gemini_score}")
            return gemini_score, gemini_feedback
        except Exception as e:
            logger.warning(f"Gemini API evaluation failed: {str(e)}. Falling back to local analysis.")
            # If Gemini fails, fall back to TextBlob analysis
            textblob_score, textblob_feedback = evaluate_with_textblob(transcribed_text)
            return textblob_score, f"[AI evaluation unavailable - using automated analysis]\n\n{textblob_feedback}"

    except Exception as e:
        logger.error(f"Error in behavioral response evaluation: {str(e)}")
        logger.error(traceback.format_exc())
        return 50.0, f"Unable to evaluate video response due to an error: {str(e)}"




def transcribe_audio(audio_path):
    """
    Improved audio transcription with better error handling and speech recognition tuning.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300  # Lower threshold for quieter audio
    recognizer.dynamic_energy_threshold = True  # Adapt to ambient noise
    
    with sr.AudioFile(audio_path) as source:
        logger.debug("Recording audio from WAV file")
        # Adjust for ambient noise to improve recognition accuracy
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.record(source)
        
        # Try multiple recognition services if available
        text = ""
        services_to_try = [
            ("Google", lambda: recognizer.recognize_google(audio, language='en-US')),
            # Add other services if available (e.g., Sphinx for offline recognition)
            ("Sphinx", lambda: recognizer.recognize_sphinx(audio)) if hasattr(recognizer, 'recognize_sphinx') else None
        ]
        
        # Remove any None values
        services_to_try = [service for service in services_to_try if service]
        
        # Try each service until one succeeds
        last_error = None
        for service_name, recognition_func in services_to_try:
            try:
                logger.debug(f"Attempting speech recognition with {service_name}")
                text = recognition_func()
                logger.info(f"Successfully transcribed with {service_name}: {text[:50]}...")
                break
            except sr.UnknownValueError:
                last_error = f"{service_name} could not understand audio"
                logger.warning(f"Speech recognition with {service_name} failed: No understandable speech detected")
            except sr.RequestError as e:
                last_error = f"{service_name} service error: {str(e)}"
                logger.error(f"Speech recognition {service_name} service error: {str(e)}")
            except Exception as e:
                last_error = f"{service_name} unexpected error: {str(e)}"
                logger.error(f"Unexpected error with {service_name}: {str(e)}")
        
        if not text:
            logger.error(f"All speech recognition services failed. Last error: {last_error}")
            
        return text


def evaluate_with_gemini_api(question_content, transcribed_text):
    """
    Evaluate the behavioral response using Gemini API with a structured prompt
    to ensure consistent scoring.
    """
    try:
        # This is where you'll use your actual Gemini API call
        # For now we'll assume `model` is your Gemini client
        from google.generativeai import GenerativeModel
        
        # Initialize the model (replace with your actual initialization)
        model = GenerativeModel("gemini-pro")  # Adjust model name as needed
        
        evaluation_prompt = f"""
        You are an expert interviewer evaluating a behavioral interview response.
        
        Question asked: "{question_content}"
        
        Transcribed Response:
        "{transcribed_text}"
        
        Evaluate the response based on the STAR method (Situation, Task, Action, Result) and provide detailed feedback in the following categories:
        
        1. Relevance (20 points): How well the response addresses the specific question
        2. Structure (20 points): Clear organization following the STAR method
        3. Detail and Specificity (20 points): Concrete examples vs vague generalities
        4. Communication Clarity (20 points): Articulation, conciseness, and flow
        5. Professionalism (20 points): Language, tone, and presentation
        
        For each category, provide:
        - A score out of 20
        - Specific strengths
        - Areas for improvement
        
        IMPORTANT: Calculate and include a total numerical score out of 100 at the end of your evaluation.
        Your response MUST include this line exactly in this format:
        "FINAL_SCORE: [number]" where [number] is a float between 0 and 100.
        """
        
        logger.debug("Sending evaluation prompt to Gemini API")
        response = model.generate_content(evaluation_prompt)
        feedback = response.text
        logger.debug(f"Received Gemini API response of length {len(feedback)}")
        
        # Extract score using regex
        score_match = re.search(r"FINAL_SCORE:\s*(\d+(?:\.\d+)?)", feedback)
        
        if score_match:
            try:
                score = float(score_match.group(1))
                logger.info(f"Successfully extracted behavioral score: {score}")
            except ValueError as e:
                logger.error(f"Failed to convert extracted score to float: {score_match.group(1)}")
                score = 50.0
        else:
            # Try alternate formats if the explicit format isn't found
            alternate_score_match = re.search(r"(?:Score|Total Score|Final Score):\s*(\d+(?:\.\d+)?)(?:/100)?", feedback, re.IGNORECASE)
            if alternate_score_match:
                try:
                    score = float(alternate_score_match.group(1))
                    logger.info(f"Extracted score from alternate format: {score}")
                except ValueError:
                    score = 50.0
            else:
                logger.warning("Could not extract score from Gemini response, defaulting to 50.0")
                feedback += "\n\nNote: The system could not extract a numerical score and defaulted to 50.0."
                score = 50.0
        
        # Clean up the feedback to remove the FINAL_SCORE line
        cleaned_feedback = re.sub(r"FINAL_SCORE:\s*\d+(?:\.\d+)?", "", feedback).strip()
        
        return score, cleaned_feedback
    
    except Exception as e:
        logger.error(f"Error in Gemini API evaluation: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def evaluate_with_textblob(text):
    """
    Fallback evaluation using TextBlob for sentiment analysis and other text metrics.
    This provides a more reliable backup if the Gemini API is unavailable.
    """
    try:
        # Enhanced TextBlob analysis with more sophisticated metrics
        blob = TextBlob(text)
        
        # Sentiment analysis (positivity/confidence)
        sentiment = blob.sentiment.polarity  # -1 to 1
        sentiment_score = ((sentiment + 1) / 2) * 100  # Convert to 0-100
        
        # Subjectivity (how personal/opinionated vs. factual)
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        subjectivity_score = 100 - (abs(0.5 - subjectivity) * 200)  # Penalize extremes
        
        # Response length and complexity
        word_count = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / max(word_count, 1)
        sentence_count = len(blob.sentences)
        
        # Calculate complexity score (ideal response is neither too simple nor too complex)
        if word_count < 20:
            length_score = word_count * 2.5  # Penalize very short responses
        elif word_count > 500:
            length_score = 100 - ((word_count - 500) / 10)  # Penalize excessive length
        else:
            length_score = 50 + min(50, word_count / 10)  # Reward moderate length
        
        length_score = max(0, min(100, length_score))  # Clamp to 0-100
        
        # Clarity analysis
        filler_words = ['um', 'uh', 'like', 'you know', 'basically', 'actually', 'literally']
        filler_count = sum(text.lower().count(filler) for filler in filler_words)
        filler_ratio = filler_count / max(word_count, 1)
        clarity_score = max(0, 100 - (filler_ratio * 500))  # Penalize for excessive fillers
        
        # Vocabulary diversity score
        unique_words = set(word.lower() for word in re.findall(r'\b\w+\b', text))
        vocabulary_diversity = len(unique_words) / max(word_count, 1)
        vocab_score = min(100, vocabulary_diversity * 200)
        
        # Calculate final score (weighted average of all metrics)
        weights = {
            'sentiment': 0.15,  # Confidence
            'subjectivity': 0.10,  # Balanced perspective
            'length': 0.25,     # Appropriate length
            'clarity': 0.30,    # Clear communication
            'vocabulary': 0.20  # Language use
        }
        
        component_scores = {
            'sentiment': sentiment_score,
            'subjectivity': subjectivity_score,
            'length': length_score,
            'clarity': clarity_score,
            'vocabulary': vocab_score
        }
        
        final_score = sum(score * weights[metric] for metric, score in component_scores.items())
        final_score = max(30, min(95, final_score))  # Ensure score is between 30-95
        
        # Generate detailed feedback
        feedback = f"""## Response Analysis

        ### Transcribed Text:
        "{text}"

        ### Evaluation Components:
        - **Response Length**: {word_count} words ({length_score:.1f}/100)
        {get_length_feedback(word_count)}

        - **Clarity Score**: {clarity_score:.1f}/100
        {get_clarity_feedback(clarity_score, filler_ratio)}

        - **Language Usage**: {vocab_score:.1f}/100
        {get_vocabulary_feedback(vocabulary_diversity)}

        - **Tone Analysis**: {sentiment_score:.1f}/100
        {get_sentiment_feedback(sentiment)}

        ### Overall Assessment:
        {get_overall_feedback(final_score)}

        ### Final Score: {final_score:.1f}/100
        """
        
        return final_score, feedback
        
    except Exception as e:
        logger.error(f"Error in TextBlob evaluation: {str(e)}")
        return 50.0, f"Unable to analyze response: {str(e)}"


# Helper functions for feedback generation
def get_length_feedback(word_count):
    if word_count < 30:
        return "Your response is very brief. Consider providing more details and examples."
    elif word_count < 100:
        return "Your response has adequate length but could benefit from additional details."
    elif word_count > 400:
        return "Your response is quite lengthy. Consider being more concise while maintaining key details."
    else:
        return "Your response has a good length with sufficient detail."

def get_clarity_feedback(clarity_score, filler_ratio):
    if filler_ratio > 0.1:
        return f"Your response contains many filler words ({filler_ratio:.1%} of words). Reducing these would improve clarity."
    elif clarity_score < 70:
        return "Work on communicating more clearly by using more precise language."
    else:
        return "You communicated clearly with minimal filler words."

def get_vocabulary_feedback(diversity):
    if diversity < 0.3:
        return "Consider using more varied vocabulary to express your ideas."
    elif diversity > 0.6:
        return "Excellent vocabulary diversity showing strong communication skills."
    else:
        return "You used a good range of vocabulary in your response."

def get_sentiment_feedback(sentiment):
    if sentiment < -0.3:
        return "Your response has a somewhat negative tone. Consider using more positive framing when appropriate."
    elif sentiment > 0.5:
        return "Your response has a confident, positive tone which is generally effective in interviews."
    else:
        return "Your response has a balanced, neutral tone appropriate for professional settings."

def get_overall_feedback(score):
    if score < 50:
        return "Your response needs significant improvement in content, structure, and delivery."
    elif score < 70:
        return "Your response was adequate but could be stronger with more structure and specific examples."
    elif score < 85:
        return "Your response was good, demonstrating solid communication skills with room for refinement."
    else:
        return "Your response was excellent, showing strong communication and thoughtful content."