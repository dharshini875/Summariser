#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
from flask import Flask, render_template, request, flash, session
import requests
from bs4 import BeautifulSoup
import os
import json

app = Flask(__name__)
app.secret_key = "your_secret_key" 

# Groq API details
API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# GOOGLE API details
# API_KEY = os.environ.get("GOOGLE_API_KEY"," YOUR_API_KEY")
# API_URL = "https://api.groq.com/openai/v1/chat/completions"




def fetch_content_from_url(url):
    print("fetch_content_from_url function called")
    try:
        response = requests.get(url)
        response.raise_for_status()  
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = ' '.join([p.get_text() for p in soup.find_all('p')])
        return main_content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        print(f"Exception type: {type(e)}")  
        return f"Error fetching URL: {e}"

def call_groq_api(api_key, model, messages, max_tokens=500): 
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    return response

def get_answer_from_response(response):
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        return f"Error: {response.status_code}, {response.text}"

def ask_question_with_content(api_key, extracted_content, question, model="llama3-8b-8192"):
    messages = [
        {"role": "system", "content": "You are an expert in answering questions based on the provided content."},
        {"role": "user", "content": f"Content: {extracted_content}\n\nQuestion: {question}"}
    ]
    response = call_groq_api(api_key, model, messages)
    answer = get_answer_from_response(response)
    return answer

def generate_quiz_questions(api_key, transcript_content, num_questions=5, model="llama3-8b-8192"):
    prompt = f"""Generate {num_questions} multiple-choice questions based on the following text.
Each question should have 4 options, labeled A, B, C, and D. Clearly indicate the correct answer for each question by starting the line with 'Correct Answer:'. Also provide a brief explanation for the correct answer starting with 'Explanation:'. Ensure each question, options, correct answer, and explanation are clearly separated.

Text:
{transcript_content}

Example Question Format for each question:
Question: [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [Letter of the correct option] [Full text of the correct option]
Explanation: [Explanation of the correct answer]

Separate each question block with '----END OF QUESTION----'.
"""
    messages = [{"role": "user", "content": prompt}]
    response = call_groq_api(api_key, model, messages, max_tokens=3000) 
    return get_answer_from_response(response).split('----END OF QUESTION----')

def summarize_content(api_key, transcript_content, model="llama3-8b-8192"):
    prompt = f"""Please summarize the following text using bullet points. Each bullet point should represent a key piece of information from the text.

Text:
{transcript_content}
"""
    messages = [{"role": "user", "content": prompt}]
    response = call_groq_api(api_key, model, messages, max_tokens=800) 
    return get_answer_from_response(response)

@app.route('/', methods=['GET', 'POST'])
def index():
    answer = None
    quiz_feedback = None
    quiz_questions = session.get('quiz_questions', [])
    current_question_index = session.get('current_question_index', 0)
    current_quiz_question = None
    summary = session.get('summary') 
    transcript_content = session.get('transcript_content') 

    show_summary = session.get('show_summary', False)
    show_quiz = session.get('show_quiz', False)
    show_ask_form = session.get('show_ask_form', False)

    if request.method == 'GET':
        session['quiz_questions'] = [] 
        session['current_question_index'] = 0
        session['summary'] = None 
        session['quiz'] = None 
        session['show_summary'] = False
        session['show_quiz'] = False
        session['show_ask_form'] = False

    if quiz_questions and current_question_index < len(quiz_questions):
        current_quiz_question = quiz_questions[current_question_index]

    if request.method == 'POST':
        link = request.form.get('link')
        question = request.form.get('question')
        transcript_file = request.files.get('transcript_file')
        youtube_transcript = request.form.get('youtube_transcript')
        generate_quiz = request.form.get('generate_quiz') 
        summarize = request.form.get('summarize') 
        ask_question_about = request.form.get('ask_question_about')
        ask = request.form.get('ask')
        quiz_answer = request.form.get('quiz_answer') 
        question_about_content = request.form.get('question_about_content')

        extracted_content = None


        if generate_quiz or summarize or ask_question_about:
            session['show_summary'] = False
            session['show_quiz'] = False
            session['show_ask_form'] = False
            session['answer'] = None

        if transcript_file and transcript_file.filename != '':
            try:
                transcript_content = transcript_file.read().decode('utf-8')
                session['transcript_content'] = transcript_content
                print("Transcript uploaded and stored in session.")
            except Exception as e:
                answer = f"Error reading uploaded file: {e}"
        elif youtube_transcript:
            extracted_content = youtube_transcript
            session['transcript_content'] = youtube_transcript
            print("YouTube transcript pasted and stored in session.")
        elif link:
            extracted_content = fetch_content_from_url(link)
            session['transcript_content'] = extracted_content
            print("Content fetched from link and stored in session.")

        elif session.get('transcript_content'):
            extracted_content = session['transcript_content']
            print("Using transcript content from session.")

        if summarize and session.get('transcript_content'):
            print("Summarize button clicked.")
            try:
                summary_text = summarize_content(API_KEY, session['transcript_content'])
                session['summary'] = summary_text
                session['show_summary'] = True
                session['show_quiz'] = False
                session['show_ask_form'] = False
                summary = session.get('summary')
                print("Summary generated and stored in session:", summary)
            except Exception as e:
                answer = f"Error generating summary: {e}"
        elif generate_quiz and session.get('transcript_content'):
            print("generate_quiz clicked")
            try:
                generated_quiz_texts = generate_quiz_questions(API_KEY, session['transcript_content'], num_questions=5) 
                quiz_question_list = []
                for q_text in generated_quiz_texts:
                    if q_text.strip():
                        question_data = {"options": [], "explanation": ""}
                        correct_answer_text_full = ""
                        for line in q_text.strip().split('\n'):
                            if line.startswith("Question:"):
                                question_data["question"] = line.split("Question:")[1].strip()
                            elif line.startswith("A)"):
                                question_data["options"].append(line.split("A)")[1].strip())
                            elif line.startswith("B)"):
                                question_data["options"].append(line.split("B)")[1].strip())
                            elif line.startswith("C)"):
                                question_data["options"].append(line.split("C)")[1].strip())
                            elif line.startswith("D)"):
                                question_data["options"].append(line.split("D)")[1].strip())
                            elif line.startswith("Correct Answer:"):
                                correct_answer_text_full = line.split("Correct Answer:")[1].strip()
                                if ")" in correct_answer_text_full:
                                    question_data["correct_answer_text"] = correct_answer_text_full.split(")")[1].strip()
                            elif line.startswith("Explanation:"):
                                question_data["explanation"] = line.split("Explanation:")[1].strip()
                        if question_data.get("question"):
                            quiz_question_list.append(question_data)

                session['quiz_questions'] = quiz_question_list
                session['current_question_index'] = 0
                session['show_quiz'] = True
                session['show_summary'] = False
                session['show_ask_form'] = False
                current_question_index = 0 
                current_quiz_question = quiz_question_list[0] if quiz_question_list else None

                print("Generated Quiz Questions (Session):", session.get('quiz_questions'))
                print("Current Question Index:", session.get('current_question_index'))

            except Exception as e:
                answer = f"Error generating quiz: {e}"
        elif ask_question_about and session.get('transcript_content'):
            session['show_ask_form'] = True
            session['show_summary'] = False
            session['show_quiz'] = False
            print("Ask a Question button clicked.")
        elif ask and session.get('transcript_content') and question_about_content:
            print("Asking question about content:", question_about_content)
            try:
                answer = ask_question_with_content(API_KEY, session['transcript_content'], question_about_content)
                session['answer'] = answer
                session['show_ask_form'] = True
                print("Answer generated for question about content.")
            except Exception as e:
                answer = f"Error asking question: {e}"
        elif current_quiz_question and quiz_answer:
            correct_answer_text = current_quiz_question.get("correct_answer_text")

            if quiz_answer == correct_answer_text:
                quiz_feedback = "Correct!"
                session['current_question_index'] += 1
                current_question_index = session.get('current_question_index')
                if current_question_index < len(quiz_questions):
                    current_quiz_question = quiz_questions[current_question_index]
                else:
                    quiz_feedback = "Quiz Completed!" 
                    current_quiz_question = None
                    session['quiz_questions'] = []
                    session['current_question_index'] = 0
                    session['show_quiz'] = False
            else:
                quiz_feedback = f"Incorrect. The correct answer was: {correct_answer_text}. Explanation: {current_quiz_question.get('explanation', '')}"

            print("Quiz Feedback:", quiz_feedback) 
            print("Current Question Index after answer:", session.get('current_question_index'))

    return render_template('index.html', answer=session.get('answer'), quiz=current_quiz_question, quiz_feedback=quiz_feedback, summary=summary, show_summary=show_summary, show_quiz=show_quiz, show_ask_form=show_ask_form)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    return index()

if __name__ == '__main__':
    app.run(debug=True)
