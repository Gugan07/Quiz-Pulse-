from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, flash, session
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User
import PyPDF2
import os
import json
import tempfile
import re
import random
from collections import Counter
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_generator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db.init_app(app)

# Configure Google Gemini AI
genai.configure(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
ai_model = genai.GenerativeModel('gemini-2.5-flash')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            })
        else:
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logout successful'})

@app.route('/api/user')
@login_required
def get_user():
    return jsonify({
        'username': current_user.username,
        'email': current_user.email
    })

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Please upload a PDF file'}), 400
 
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            pdf_text = extract_text_from_pdf(temp_file.name)
        
    
        os.unlink(temp_file.name)
        
        if not pdf_text.strip():
            return jsonify({'error': 'Could not extract text from PDF. The file might be scanned or empty.'}), 400
        
        return jsonify({
            'success': True,
            'text': pdf_text,
            'fileName': file.filename
        })
    
    except Exception as e:
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.json
        pdf_text = data.get('text', '')
        quiz_type = data.get('quiz_type', 'multiple_choice')
        question_count = int(data.get('question_count', 5))
        difficulty = data.get('difficulty', 'medium')
        
        if not pdf_text:
            return jsonify({'error': 'No text provided for quiz generation'}), 400
        
        print(f"🎯 Creating {question_count} professional {quiz_type} questions from PDF content...")
       
        quiz = generate_professional_quiz(pdf_text, quiz_type, question_count, difficulty)
        
        return jsonify({
            'success': True,
            'quiz': quiz
        })
    
    except Exception as e:
        print(f"❌ Error in generate_quiz: {str(e)}")
        return jsonify({'error': f'Error generating quiz: {str(e)}'}), 500

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")

def extract_quiz_content(pdf_text):
    """Extract actual content that can be used for quiz questions"""
    
    # Split into sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', pdf_text) if len(s.strip()) > 10]
    
    # Find factual statements (sentences with specific information)
    factual_sentences = []
    for sentence in sentences:
        if (len(sentence.split()) >= 6 and 
            any(char.isdigit() for char in sentence) or
            any(word.istitle() for word in sentence.split() if len(word) > 3)):
            factual_sentences.append(sentence)
    
    # Extract specific data points
    numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', pdf_text)
    dates = re.findall(r'\b(?:19|20)\d{2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', pdf_text)
    
    # Extract names and proper nouns
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', pdf_text)
    common_proper_nouns = Counter(proper_nouns).most_common(10)
    
    # Find comparison statements
    comparisons = [s for s in sentences if any(word in s.lower() for word in 
                  ['higher', 'lower', 'greater', 'less', 'more', 'less', 'compared', 'than', 'versus'])]
    
    # Find cause-effect statements
    cause_effect = [s for s in sentences if any(word in s.lower() for word in 
                   ['because', 'therefore', 'thus', 'consequently', 'as a result', 'due to'])]
    
    # Find definition statements
    definitions = [s for s in sentences if any(word in s.lower() for word in 
                 ['defined as', 'means', 'refers to', 'is called', 'known as'])]
    
    return {
        'sentences': sentences[:50],  # First 50 sentences
        'factual_sentences': factual_sentences[:20],
        'numbers': numbers[:15],
        'dates': dates[:10],
        'key_terms': [term for term, count in common_proper_nouns if count > 1][:8],
        'comparisons': comparisons[:10],
        'cause_effect': cause_effect[:10],
        'definitions': definitions[:10]
    }

def generate_professional_quiz(pdf_text, quiz_type, question_count, difficulty):
    """Generate professional, AI-powered quiz questions from PDF content"""

    print("🤖 Using Google Gemini AI to generate high-quality quiz questions...")

    try:
        # Create AI prompt for quiz generation
        if quiz_type == 'multiple_choice':
            options_format = '"options": ["Option A", "Option B", "Option C", "Option D"]'
            correct_format = '"correctAnswer": 0  // index of correct option (0-3)'
        elif quiz_type == 'true_false':
            options_format = '"options": ["True", "False"]'
            correct_format = '"correctAnswer": 0  // 0 for True, 1 for False'
        else:  # short_answer
            options_format = ' // no options field for short_answer'
            correct_format = '"correctAnswer": "Expected answer text"'

        prompt = f"""
        You are an expert educator creating high-quality quiz questions from a PDF document.

        DOCUMENT CONTENT:
        {pdf_text[:8000]}  # Limit content length for API

        TASK: Create {question_count} {quiz_type} questions that test understanding of the key concepts, facts, and information in this document.

        REQUIREMENTS:
        - Questions must be based DIRECTLY on information in the document
        - Questions should test comprehension, not just memorization
        - Difficulty level: {difficulty}
        - Questions should be professional and academic in tone

        FORMAT: Return a JSON array of question objects with this structure:
        [
            {{
                "id": 1,
                "question": "Question text here",
                "type": "{quiz_type}",
                {options_format},
                {correct_format}
            }}
        ]

        IMPORTANT: Ensure questions are accurate and directly supported by the document content.
        """

        response = ai_model.generate_content(prompt)
        ai_response = response.text.strip()

        # Clean up the response to extract JSON
        if ai_response.startswith('```json'):
            ai_response = ai_response[7:]
        if ai_response.endswith('```'):
            ai_response = ai_response[:-3]

        ai_response = ai_response.strip()

        try:
            questions = json.loads(ai_response)
            print(f"✅ AI generated {len(questions)} high-quality quiz questions")
            return {'questions': questions}
        except json.JSONDecodeError as e:
            print(f"❌ AI response parsing failed: {e}")
            print(f"AI Response: {ai_response[:500]}...")
            # Fallback to rule-based generation
            return generate_fallback_quiz(pdf_text, quiz_type, question_count, difficulty)

    except Exception as e:
        print(f"❌ AI generation failed: {e}")
        # Fallback to rule-based generation
        return generate_fallback_quiz(pdf_text, quiz_type, question_count, difficulty)

def generate_fallback_quiz(pdf_text, quiz_type, question_count, difficulty):
    """Fallback rule-based quiz generation when AI fails"""

    print("🔄 Falling back to rule-based quiz generation...")
    content = extract_quiz_content(pdf_text)

    questions = []

    for i in range(question_count):
        if quiz_type == 'multiple_choice':
            question = create_professional_mc_question(content, i, difficulty)
        elif quiz_type == 'true_false':
            question = create_professional_tf_question(content, i, difficulty)
        else:  # short_answer
            question = create_professional_sa_question(content, i, difficulty)

        questions.append(question)

    print(f"✅ Created {len(questions)} fallback quiz questions")
    return {'questions': questions}

def create_professional_mc_question(content, index, difficulty):
    """Create professional multiple choice questions using REAL PDF content"""
    available_content = []
    
    if content['factual_sentences']:
        available_content.append('factual')
    if content['numbers']:
        available_content.append('numerical')
    if content['dates']:
        available_content.append('temporal')
    if content['key_terms']:
        available_content.append('definition')
    if content['comparisons']:
        available_content.append('comparison')
    if content['cause_effect']:
        available_content.append('cause_effect')
    
    if not available_content:
        available_content = ['general']
    
    content_type = random.choice(available_content)
    
    if content_type == 'factual' and content['factual_sentences']:

        sentence = random.choice(content['factual_sentences'])
        words = sentence.split()
        
        if len(words) >= 8:
            # Create fill-in-the-blank from actual sentence
            blank_index = random.randint(3, len(words) - 3)
            correct_answer = words[blank_index]
            question_text = ' '.join(words[:blank_index] + ['__________'] + words[blank_index+1:])
            
            options = [correct_answer]
            # Add plausible distractors from same PDF
            for _ in range(3):
                distractor = generate_plausible_distractor(content, correct_answer)
                options.append(distractor)
            
            random.shuffle(options)
            correct_index = options.index(correct_answer)
            
            return {
                'id': index + 1,
                'question': f'Complete this sentence from the document: "{question_text}"',
                'type': 'multiple_choice',
                'options': options,
                'correctAnswer': correct_index
            }
    
    elif content_type == 'numerical' and content['numbers']:
        # Question about specific numbers in the document
        number = random.choice(content['numbers'])
        question_text = f'What specific numerical value is mentioned in the document?'
        
        options = [number]
        for _ in range(3):
            if '%' in number:
                options.append(f"{random.randint(1, 100)}%")
            else:
                try:
                    num_val = float(number.replace('%', ''))
                    options.append(str(round(num_val * random.uniform(0.5, 2.0), 1)) + ('%' if '%' in number else ''))
                except:
                    options.append(str(random.randint(1, 100)))
        
        random.shuffle(options)
        correct_index = options.index(number)
        
        return {
            'id': index + 1,
            'question': question_text,
            'type': 'multiple_choice',
            'options': options,
            'correctAnswer': correct_index
        }
    
    elif content_type == 'temporal' and content['dates']:
        # Question about dates
        date = random.choice(content['dates'])
        question_text = f'What specific date or year is referenced in the document?'
        
        options = [date]
        for _ in range(3):
            if len(date) == 4 and date.isdigit():  # Year
                year = int(date)
                options.append(str(year + random.choice([-5, -2, 2, 5])))
            else:
                options.append(generate_plausible_date())
        
        random.shuffle(options)
        correct_index = options.index(date)
        
        return {
            'id': index + 1,
            'question': question_text,
            'type': 'multiple_choice',
            'options': options,
            'correctAnswer': correct_index
        }
    
    elif content_type == 'definition' and content['key_terms']:
        # Question about key terms
        term = random.choice(content['key_terms'])
        question_text = f'What is mentioned about "{term}" in the document?'
        
        options = [
            f'Key information specifically discussed in the text',
            f'Details not found in the document',
            f'Opposite interpretation of the actual content',
            f'Unrelated concept not mentioned'
        ]
        
        return {
            'id': index + 1,
            'question': question_text,
            'type': 'multiple_choice',
            'options': options,
            'correctAnswer': 0
        }
    
    # High-quality fallback question
    if content['sentences']:
        context_sentence = random.choice(content['sentences'][:10])
        question_text = f'Based on the document content, what specific detail is accurate?'
        
        options = [
            'Information directly stated in the text',
            'Contradictory information not supported',
            'External assumption without basis',
            'Incorrect interpretation of facts'
        ]
    else:
        question_text = 'What specific information from the document supports the main arguments?'
        options = [
            'Evidence and examples provided in the text',
            'Information not present in the document',
            'Personal opinions without support',
            'Contradictory statements'
        ]
    
    return {
        'id': index + 1,
        'question': question_text,
        'type': 'multiple_choice',
        'options': options,
        'correctAnswer': 0
    }

def create_professional_tf_question(content, index, difficulty):
    """Create professional True/False questions using REAL content"""
    
    if content['factual_sentences']:
        sentence = random.choice(content['factual_sentences'])
        words = sentence.split()
        
        if len(words) > 6:
            statement = sentence.replace('?', '.')
            if not statement.endswith('.'):
                statement += '.'
            is_true = random.random() < 0.8
            
            if not is_true:

                words = statement.split()
                if len(words) > 4:
                    # Change a key word to make it false
                    change_index = random.randint(2, len(words) - 2)
                    original_word = words[change_index]
                    words[change_index] = get_opposite_word(original_word)
                    statement = ' '.join(words)
            
            return {
                'id': index + 1,
                'question': statement,
                'type': 'true_false',
                'options': ['True', 'False'],
                'correctAnswer': 0 if is_true else 1
            }
    
    # Fallback professional TF question
    statement = "The document provides specific evidence and factual information to support its claims."
    return {
        'id': index + 1,
        'question': statement,
        'type': 'true_false',
        'options': ['True', 'False'],
        'correctAnswer': 0
    }

def create_professional_sa_question(content, index, difficulty):
    """Create professional Short Answer questions"""
    
    if content['key_terms'] and content['factual_sentences']:
        term = random.choice(content['key_terms'])
        question_text = f'What specific information does the document provide about {term}?'
        answer_guide = 'Provide details, examples, or explanations mentioned in the document'
    elif content['factual_sentences']:
        question_text = 'What evidence or examples from the document support its primary conclusions?'
        answer_guide = 'Reference specific facts, data, or instances mentioned in the text'
    else:
        question_text = 'What are the key findings or main points presented in the document?'
        answer_guide = 'Summarize the main arguments and supporting evidence from the text'
    
    return {
        'id': index + 1,
        'question': question_text,
        'type': 'short_answer',
        'correctAnswer': answer_guide
    }

def generate_plausible_distractor(content, correct_answer):
    """Generate plausible wrong answers based on PDF content"""
    
    # Try to use content from the same PDF
    if content['numbers'] and any(c.isdigit() for c in correct_answer):
        other_numbers = [n for n in content['numbers'] if n != correct_answer]
        if other_numbers:
            return random.choice(other_numbers)
    
    if content['key_terms']:
        other_terms = [t for t in content['key_terms'] if t != correct_answer]
        if other_terms:
            return random.choice(other_terms)
    
    distractors = [
        'Incorrect interpretation',
        'Not mentioned in document',
        'Contradicts text content',
        'Unsupported assumption'
    ]
    return random.choice(distractors)

def generate_plausible_date():
    """Generate plausible date distractors"""
    year = random.randint(1990, 2025)
    if random.random() > 0.5:
        return str(year)
    else:
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{month:02d}/{day:02d}/{year}"

def get_opposite_word(word):
    """Get an opposite or contradictory word"""
    opposites = {
        'increased': 'decreased',
        'higher': 'lower',
        'more': 'less',
        'positive': 'negative',
        'successful': 'unsuccessful',
        'effective': 'ineffective',
        'significant': 'insignificant',
        'strong': 'weak',
        'improved': 'worsened',
        'better': 'worse'
    }
    return opposites.get(word.lower(), 'not ' + word)

@app.route('/api/analyze-pdf', methods=['POST'])
def analyze_pdf():
    """Endpoint to see what content was extracted from PDF"""
    try:
        data = request.json
        pdf_text = data.get('text', '')
        
        if not pdf_text:
            return jsonify({'error': 'No text provided'}), 400
        
        content = extract_quiz_content(pdf_text)
        
        return jsonify({
            'success': True,
            'analysis': {
                'total_sentences': len(content['sentences']),
                'factual_sentences_sample': content['factual_sentences'][:3],
                'key_terms': content['key_terms'],
                'numbers_found': content['numbers'][:5],
                'dates_found': content['dates'][:3],
                'content_quality': 'Excellent' if len(content['factual_sentences']) > 5 else 'Good'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    print("=" * 60)
    print("🚀 PROFESSIONAL QUIZ GENERATOR")
    print("🤖 Powered by Google Gemini AI")
    print("🎯 Real Exam-Quality Questions")
    print("📊 AI-Enhanced PDF Analysis")
    print("=" * 60)

    app.run(debug=True, port=5000)
