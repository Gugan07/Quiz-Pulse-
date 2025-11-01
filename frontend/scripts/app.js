// API Base URL
const API_BASE_URL = 'http://localhost:5000/api';

// Auth state
let currentUser = null;

// DOM Elements
const uploadSection = document.getElementById('uploadSection');
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const fileName = document.getElementById('fileName');
const quizOptionsSection = document.getElementById('quizOptionsSection');
const generateQuizBtn = document.getElementById('generateQuizBtn');
const loadingSection = document.getElementById('loadingSection');
const quizPreviewSection = document.getElementById('quizPreviewSection');
const quizPreview = document.getElementById('quizPreview');
const startQuizBtn = document.getElementById('startQuizBtn');
const regenerateBtn = document.getElementById('regenerateBtn');
const quizTakingSection = document.getElementById('quizTakingSection');
const currentQuestionText = document.getElementById('currentQuestionText');
const optionsContainer = document.getElementById('optionsContainer');
const prevQuestionBtn = document.getElementById('prevQuestionBtn');
const nextQuestionBtn = document.getElementById('nextQuestionBtn');
const submitQuizBtn = document.getElementById('submitQuizBtn');
const progressBar = document.getElementById('progressBar');
const resultsSection = document.getElementById('resultsSection');
const scoreDisplay = document.getElementById('scoreDisplay');
const scoreMessage = document.getElementById('scoreMessage');
const retakeQuizBtn = document.getElementById('retakeQuizBtn');
const newQuizBtn = document.getElementById('newQuizBtn');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const quizTimer = document.getElementById('quizTimer');

// Auth DOM Elements
const authSection = document.getElementById('authSection');
const authButtons = document.getElementById('authButtons');
const userInfo = document.getElementById('userInfo');
const userDisplay = document.getElementById('userDisplay');
const loginBtn = document.getElementById('loginBtn');
const signupBtn = document.getElementById('signupBtn');
const logoutBtn = document.getElementById('logoutBtn');
const authModal = document.getElementById('authModal');
const closeModal = document.getElementById('closeModal');
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const loginFormElement = document.getElementById('loginFormElement');
const signupFormElement = document.getElementById('signupFormElement');
const switchToSignup = document.getElementById('switchToSignup');
const switchToLogin = document.getElementById('switchToLogin');

// Quiz state
let currentQuiz = null;
let currentQuestionIndex = 0;
let userAnswers = [];
let timerInterval = null;
let timeLeft = 600; // 10 minutes in seconds
let extractedText = '';

// Event Listeners
browseBtn.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--primary)';
    uploadArea.style.backgroundColor = 'rgba(67, 97, 238, 0.05)';
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#ccc';
    uploadArea.style.backgroundColor = 'transparent';
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#ccc';
    uploadArea.style.backgroundColor = 'transparent';
    
    if (e.dataTransfer.files.length) {
        handleFileSelection(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFileSelection(e.target.files[0]);
    }
});

// Auth Event Listeners
loginBtn.addEventListener('click', () => showAuthModal('login'));
signupBtn.addEventListener('click', () => showAuthModal('signup'));
logoutBtn.addEventListener('click', logout);
closeModal.addEventListener('click', () => authModal.classList.add('hidden'));
switchToSignup.addEventListener('click', (e) => {
    e.preventDefault();
    showAuthModal('signup');
});
switchToLogin.addEventListener('click', (e) => {
    e.preventDefault();
    showAuthModal('login');
});
loginFormElement.addEventListener('submit', handleLogin);
signupFormElement.addEventListener('submit', handleSignup);

// Quiz Event Listeners
generateQuizBtn.addEventListener('click', generateQuiz);
startQuizBtn.addEventListener('click', startQuiz);
regenerateBtn.addEventListener('click', generateQuiz);
prevQuestionBtn.addEventListener('click', showPreviousQuestion);
nextQuestionBtn.addEventListener('click', showNextQuestion);
submitQuizBtn.addEventListener('click', submitQuiz);
retakeQuizBtn.addEventListener('click', retakeQuiz);
newQuizBtn.addEventListener('click', createNewQuiz);

// Functions
async function handleFileSelection(file) {
    if (file.type !== 'application/pdf') {
        showError('Please select a PDF file.');
        return;
    }
    
    fileName.textContent = `Selected: ${file.name}`;
    fileName.classList.remove('hidden');
    quizOptionsSection.classList.remove('hidden');
    errorMessage.classList.add('hidden');
    
    // Show loading while uploading
    loadingSection.classList.remove('hidden');
    uploadSection.classList.add('hidden');
    
    try {
        // Upload PDF to backend
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
            method: 'POST',
            body: formData,
            credentials: 'include'  // Include cookies for session
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to upload PDF');
        }
        
        extractedText = data.text;
        currentQuiz = {
            fileName: file.name,
            file: file
        };
        
        loadingSection.classList.add('hidden');
        quizOptionsSection.classList.remove('hidden');
        
    } catch (error) {
        console.error('Upload error:', error);
        loadingSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        showError(error.message);
    }
}

async function generateQuiz() {
    const quizType = document.getElementById('quizType').value;
    const questionCount = parseInt(document.getElementById('questionCount').value);
    const difficulty = document.getElementById('difficulty').value;
    
    // Show loading section
    quizOptionsSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    errorMessage.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-quiz`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',  // Include cookies for session
            body: JSON.stringify({
                text: extractedText,
                quiz_type: quizType,
                question_count: questionCount,
                difficulty: difficulty
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate quiz');
        }
        
        currentQuiz = {
            ...currentQuiz,
            ...data.quiz
        };
        
        // Show quiz preview
        loadingSection.classList.add('hidden');
        displayQuizPreview();
        quizPreviewSection.classList.remove('hidden');
        
    } catch (error) {
        console.error('Quiz generation error:', error);
        loadingSection.classList.add('hidden');
        quizOptionsSection.classList.remove('hidden');
        showError(error.message);
    }
}

function displayQuizPreview() {
    quizPreview.innerHTML = '';
    
    if (!currentQuiz.questions || currentQuiz.questions.length === 0) {
        quizPreview.innerHTML = '<p>No questions generated. Please try again.</p>';
        return;
    }
    
    currentQuiz.questions.forEach((question, index) => {
        const questionElement = document.createElement('div');
        questionElement.className = 'question-item';
        
        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.textContent = `${index + 1}. ${question.question}`;
        questionElement.appendChild(questionText);
        
        if (question.type === 'multiple_choice' || question.type === 'true_false') {
            const optionsList = document.createElement('ul');
            optionsList.className = 'options-list';
            
            question.options.forEach(option => {
                const optionItem = document.createElement('li');
                optionItem.className = 'option-item';
                optionItem.textContent = option;
                optionsList.appendChild(optionItem);
            });
            
            questionElement.appendChild(optionsList);
        }
        
        quizPreview.appendChild(questionElement);
    });
}

function startQuiz() {
    quizPreviewSection.classList.add('hidden');
    quizTakingSection.classList.remove('hidden');
    
    // Initialize quiz state
    currentQuestionIndex = 0;
    userAnswers = new Array(currentQuiz.questions.length).fill(null);
    
    // Start timer
    startTimer();
    
    // Display first question
    displayQuestion(currentQuestionIndex);
    updateNavigationButtons();
}

function displayQuestion(index) {
    const question = currentQuiz.questions[index];
    currentQuestionText.textContent = `${index + 1}. ${question.question}`;
    
    optionsContainer.innerHTML = '';
    
    if (question.type === 'multiple_choice' || question.type === 'true_false') {
        question.options.forEach((option, optionIndex) => {
            const optionElement = document.createElement('div');
            optionElement.className = 'option';
            if (userAnswers[index] === optionIndex) {
                optionElement.classList.add('selected');
            }
            optionElement.textContent = option;
            optionElement.addEventListener('click', () => selectOption(optionIndex));
            optionsContainer.appendChild(optionElement);
        });
    } else if (question.type === 'short_answer') {
        const inputElement = document.createElement('input');
        inputElement.type = 'text';
        inputElement.placeholder = 'Type your answer here...';
        inputElement.className = 'option';
        inputElement.value = userAnswers[index] || '';
        inputElement.addEventListener('input', (e) => {
            userAnswers[index] = e.target.value;
        });
        optionsContainer.appendChild(inputElement);
    }
    
    // Update progress bar
    progressBar.style.width = `${((index + 1) / currentQuiz.questions.length) * 100}%`;
}

function selectOption(optionIndex) {
    userAnswers[currentQuestionIndex] = optionIndex;
    
    // Update UI to show selected option
    const options = optionsContainer.querySelectorAll('.option');
    options.forEach((option, index) => {
        if (index === optionIndex) {
            option.classList.add('selected');
        } else {
            option.classList.remove('selected');
        }
    });
}

function showPreviousQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        displayQuestion(currentQuestionIndex);
        updateNavigationButtons();
    }
}

function showNextQuestion() {
    if (currentQuestionIndex < currentQuiz.questions.length - 1) {
        currentQuestionIndex++;
        displayQuestion(currentQuestionIndex);
        updateNavigationButtons();
    }
}

function updateNavigationButtons() {
    prevQuestionBtn.disabled = currentQuestionIndex === 0;
    
    if (currentQuestionIndex === currentQuiz.questions.length - 1) {
        nextQuestionBtn.classList.add('hidden');
        submitQuizBtn.classList.remove('hidden');
    } else {
        nextQuestionBtn.classList.remove('hidden');
        submitQuizBtn.classList.add('hidden');
    }
}

function startTimer() {
    timeLeft = 600; // 10 minutes
    updateTimerDisplay();
    
    timerInterval = setInterval(() => {
        timeLeft--;
        updateTimerDisplay();
        
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            submitQuiz();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    quizTimer.textContent = `Time: ${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function submitQuiz() {
    clearInterval(timerInterval);
    
    // Calculate score
    let score = 0;
    currentQuiz.questions.forEach((question, index) => {
        if (question.type === 'multiple_choice' || question.type === 'true_false') {
            if (userAnswers[index] === question.correctAnswer) {
                score++;
            }
        } else if (question.type === 'short_answer') {
            // For short answer, we'll give points for any non-empty answer in demo
            // In a real app, you'd implement more sophisticated checking
            if (userAnswers[index] && userAnswers[index].trim() !== '') {
                score++;
            }
        }
    });
    
    // Display results
    quizTakingSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    
    scoreDisplay.textContent = `${score}/${currentQuiz.questions.length}`;
    
    // Set score message based on performance
    const percentage = (score / currentQuiz.questions.length) * 100;
    if (percentage >= 80) {
        scoreMessage.textContent = 'Excellent! You have mastered this material.';
    } else if (percentage >= 60) {
        scoreMessage.textContent = 'Good job! You have a solid understanding.';
    } else if (percentage >= 40) {
        scoreMessage.textContent = 'Not bad! Review the material and try again.';
    } else {
        scoreMessage.textContent = 'Keep studying! You\'ll get better with practice.';
    }
}

function retakeQuiz() {
    resultsSection.classList.add('hidden');
    startQuiz();
}

function createNewQuiz() {
    resultsSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    fileName.classList.add('hidden');
    quizOptionsSection.classList.add('hidden');
    currentQuiz = null;
    extractedText = '';
}

// Auth Functions
function showAuthModal(type) {
    authModal.classList.remove('hidden');
    if (type === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
    } else {
        signupForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Login failed');
        }

        currentUser = data.user;
        updateAuthUI();
        authModal.classList.add('hidden');
        showError(''); // Clear any previous errors
        console.log('User logged in:', currentUser);

    } catch (error) {
        showError(error.message);
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const username = document.getElementById('signupUsername').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;

    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Signup failed');
        }

        currentUser = data.user;
        updateAuthUI();
        authModal.classList.add('hidden');
        showError(''); // Clear any previous errors

    } catch (error) {
        showError(error.message);
    }
}

function logout() {
    currentUser = null;
    updateAuthUI();
    // Reset to initial state
    uploadSection.classList.remove('hidden');
    quizOptionsSection.classList.add('hidden');
    loadingSection.classList.add('hidden');
    quizPreviewSection.classList.add('hidden');
    quizTakingSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    fileName.classList.add('hidden');
    currentQuiz = null;
    extractedText = '';
}

function updateAuthUI() {
    if (currentUser) {
        authButtons.classList.add('hidden');
        userInfo.classList.remove('hidden');
        userDisplay.textContent = `Welcome, ${currentUser.username}!`;
    } else {
        authButtons.classList.remove('hidden');
        userInfo.classList.add('hidden');
    }
}

function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('AI Quiz Generator initialized');
    updateAuthUI();
});
