# routes/pages.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from datetime import datetime, timedelta
from bson import ObjectId
import subprocess
import tempfile
import os
from config import db  # Add this line to import db
from functools import wraps  # Make sure this is imported for the login_required decorator

def calculate_user_stats(student_id):
    from config import db
    
    # Get all attempts for the user
    attempts = list(db.quiz_attempts.find({'student_id': student_id}))
    
    # Calculate basic stats
    total_attempts = len(attempts)
    if total_attempts == 0:
        return {
            'total_attempts': 0,
            'success_rate': 0,
            'completed_questions': 0,
            'current_streak': 0,
            'difficulty_distribution': {'easy': 0, 'medium': 0, 'hard': 0}
        }
    
    # Calculate success rate
    correct_answers = sum(attempt['score'] for attempt in attempts)
    total_questions = sum(attempt['total_questions'] for attempt in attempts)
    success_rate = round((correct_answers / total_questions * 100) if total_questions > 0 else 0, 1)
    
    # Calculate streak
    current_streak = calculate_streak(attempts)
    
    # Get completed unique questions
    completed_questions = len(set(str(answer) for attempt in attempts for answer in attempt['answers'].keys()))
    
    # Calculate difficulty distribution
    difficulty_distribution = {
        'easy': 0,
        'medium': 0,
        'hard': 0
    }
    
    for attempt in attempts:
        for question_id in attempt['answers'].keys():
            question = db.questions.find_one({'_id': ObjectId(question_id)})
            if question and 'difficulty' in question:
                difficulty_distribution[question['difficulty']] += 1
    
    return {
        'total_attempts': total_attempts,
        'success_rate': success_rate,
        'completed_questions': completed_questions,
        'current_streak': current_streak,
        'difficulty_distribution': difficulty_distribution
    }

def calculate_streak(attempts):
    if not attempts:
        return 0
    
    streak = 0
    current_date = datetime.utcnow().date()
    
    # Sort attempts by date, most recent first
    sorted_attempts = sorted(attempts, key=lambda x: x['timestamp'], reverse=True)
    
    for attempt in sorted_attempts:
        attempt_date = attempt['timestamp'].date()
        if (current_date - attempt_date).days <= 1:
            if attempt['score'] > 0:
                streak += 1
            current_date = attempt_date
        else:
            break
    
    return streak

def get_progress_data(student_id):
    from config import db
    
    # Get all attempts for the user
    attempts = list(db.quiz_attempts.find(
        {'student_id': student_id},
        sort=[('timestamp', 1)]  # Sort by date ascending
    ))
    
    dates = []
    progress_data = []
    completed_questions = set()
    
    for attempt in attempts:
        date = attempt['timestamp'].strftime('%Y-%m-%d')
        completed_questions.update(attempt['answers'].keys())
        dates.append(date)
        progress_data.append(len(completed_questions))
    
    return dates, progress_data

def get_leaderboard_data():
    from config import db
    
    # Get all users who have attempted quizzes
    pipeline = [
        {
            '$group': {
                '_id': '$student_id',
                'total_score': {'$sum': '$score'},
                'questions_solved': {'$addToSet': '$answers'},
                'last_active': {'$max': '$timestamp'}
            }
        },
        {
            '$project': {
                'rollno': '$_id',
                'total_score': 1,
                'questions_solved': {'$size': '$questions_solved'},
                'last_active': 1
            }
        },
        {'$sort': {'total_score': -1, 'questions_solved': -1}},
        {'$limit': 10}
    ]
    
    leaderboard = list(db.quiz_attempts.aggregate(pipeline))
    
    # Calculate success rate for each user
    for user in leaderboard:
        attempts = list(db.quiz_attempts.find({'student_id': user['rollno']}))
        total_questions = sum(attempt['total_questions'] for attempt in attempts)
        total_correct = sum(attempt['score'] for attempt in attempts)
        user['success_rate'] = round((total_correct / total_questions * 100) if total_questions > 0 else 0, 1)
    
    return leaderboard

pages_bp = Blueprint('pages', __name__)


# Decorator to ensure login
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'rollno' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@pages_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@pages_bp.route('/progress')
@login_required
def progress():
    from config import db
    try:
        # Get current user's attempts with error handling
        user_attempts = list(db.quiz_attempts.find({'student_id': session['rollno']}))
        
        # Calculate statistics
        stats = calculate_user_stats(session['rollno'])
        
        # Get progress data for chart
        dates, progress_data = get_progress_data(session['rollno'])
        
        # Get leaderboard data
        leaderboard = get_leaderboard_data()
        
        return render_template('progress.html',
                             stats=stats,
                             dates=dates,
                             progress_data=progress_data,
                             leaderboard=leaderboard)
                             
    except Exception as e:
        # Log the error
        print(f"Error in progress route: {str(e)}")
        
        # Return empty data with error message
        flash("There was an error loading your progress data. Please try again later.", "error")
        return render_template('progress.html',
                             stats={
                                 'total_attempts': 0,
                                 'success_rate': 0,
                                 'completed_questions': 0,
                                 'current_streak': 0,
                                 'difficulty_distribution': {'easy': 0, 'medium': 0, 'hard': 0}
                             },
                             dates=[],
                             progress_data=[],
                             leaderboard=[])


@pages_bp.route('/quiz', methods=['GET'])
@login_required
def quiz():
    from config import db
    # Fetch questions from the database
    questions = list(db.questions.find({}))
    return render_template('quiz.html', questions=questions)

@pages_bp.route('/run_tests', methods=['POST'])
@login_required
def run_tests():
    from config import db
    data = request.get_json()
    question_id = data.get('question_id')
    code = data.get('code')

    # Get the question from the database
    question = db.questions.find_one({'_id': ObjectId(question_id)})
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    # Create a temporary file to run the code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name

    try:
        # Run the test cases
        results = []
        
        # Create test environment
        test_globals = {}
        exec(code, test_globals)
        
        # Run actual test cases
        import sys
        from io import StringIO

        def run_test_and_capture_output(code_to_run, test_globals):
            # Capture stdout
            old_stdout = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output

            try:
                # Execute the code in the captured environment
                exec(code_to_run, test_globals)
                output = redirected_output.getvalue()
                return output
            finally:
                sys.stdout = old_stdout

        if 'test_cases' in question:
            for test_case in question['test_cases']:
                try:
                    # For each test case, run the submitted code in a fresh environment
                    test_globals = {}
                    
                    # Execute the test and capture output
                    actual_output = run_test_and_capture_output(code, test_globals)
                    
                    # Get expected output
                    expected_output = test_case.get('expected_output', '')
                    
                    # Compare results (strip whitespace and newlines)
                    expected_cleaned = str(expected_output).strip()
                    actual_cleaned = actual_output.strip()
                    
                    passed = actual_cleaned == expected_cleaned
                    results.append({
                        'passed': passed,
                        'expected': expected_cleaned,
                        'actual': actual_cleaned if not passed else None
                    })
                except Exception as e:
                    results.append({
                        'passed': False,
                        'error': str(e)
                    })
        else:
            # If no test cases defined, run against the main expected output
            try:
                if question.get('expected_output'):
                    # Create fresh environment
                    test_globals = {}
                    
                    # Execute the code and capture output
                    actual_output = run_test_and_capture_output(code, test_globals)
                    
                    expected_cleaned = str(question['expected_output']).strip()
                    actual_cleaned = actual_output.strip()
                    
                    passed = actual_cleaned == expected_cleaned
                    results.append({
                        'passed': passed,
                        'expected': expected_cleaned,
                        'actual': actual_cleaned if not passed else None
                    })
            except Exception as e:
                results.append({
                    'passed': False,
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'test_cases': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)

@pages_bp.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    from config import db
    answers = {}
    score = 0
    total_questions = 0
    
    # Get all questions for validation
    questions = list(db.questions.find({}))
    
    for question in questions:
        answer_key = f"answer_{question['_id']}"
        if answer_key in request.form:
            total_questions += 1
            student_answer = request.form[answer_key]
            answers[str(question['_id'])] = student_answer
            
            # Check if answer is correct
            if 'correct_answer' in question and student_answer == question['correct_answer']:
                score += 1
    
    # Store the quiz attempt in database with additional tracking
    quiz_attempt = {
        'student_id': session['rollno'],
        'answers': answers,
        'score': score,
        'total_questions': total_questions,
        'timestamp': datetime.utcnow(),
        'difficulty_scores': {
            'easy': 0,
            'medium': 0,
            'hard': 0
        }
    }
    
    # Track difficulty-wise scores
    for question in questions:
        if str(question['_id']) in answers and 'difficulty' in question:
            if answers[str(question['_id'])] == question.get('correct_answer'):
                quiz_attempt['difficulty_scores'][question['difficulty']] += 1
    
    db.quiz_attempts.insert_one(quiz_attempt)
    
    flash(f'Quiz submitted! Your score: {score}/{total_questions}', 'success')
    return redirect(url_for('pages.dashboard'))


@pages_bp.route('/quiz/submit', methods=['POST'])
@login_required
def submit_code():
    code = request.form['code']
    language = request.form['language']
    question_id = request.form['question_id']

    # For now, support only question 1 with hardcoded test cases
    test_input_list = ["2", "5", "10"]
    expected_output_list = ["4", "25", "100"]

    if language == 'python':
        result = run_python_code(code, test_input_list, expected_output_list)
    elif language == 'java':
        result = run_java_code(code, test_input_list, expected_output_list)
    else:
        result = "❌ Unsupported language."

    return render_template('quiz.html', result=result)



# Run Python code and compare output
def run_python_code(code, test_input_list, expected_output_list):
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as f:
            f.write(code + "\n")
            for i, test_input in enumerate(test_input_list):
                f.write(f"print(square({test_input}))\n")
            f.flush()

        completed = subprocess.run(["python", f.name], capture_output=True, text=True, timeout=5)
        output_lines = completed.stdout.strip().splitlines()

        results = []
        for i, (out, expected) in enumerate(zip(output_lines, expected_output_list)):
            if out.strip() == expected:
                results.append(f"✅ Test case {i+1} passed.")
            else:
                results.append(f"❌ Test case {i+1} failed. Output: {out}, Expected: {expected}")

        return "<br>".join(results)

    except Exception as e:
        return f"⚠️ Error: {str(e)}"
    finally:
        os.unlink(f.name)



# Run Java code and compare output
def run_java_code(code, test_input_list, expected_output_list):
    try:
        with tempfile.TemporaryDirectory() as tmpdirname:
            java_file = os.path.join(tmpdirname, "Main.java")
            with open(java_file, "w") as f:
                f.write(code)

            compile_proc = subprocess.run(["javac", java_file], capture_output=True, text=True)
            if compile_proc.returncode != 0:
                return f"🛑 Compilation Error:\n{compile_proc.stderr}"

            results = []
            for i, test_input in enumerate(test_input_list):
                run_proc = subprocess.run(
                    ["java", "-cp", tmpdirname, "Main", test_input],
                    capture_output=True, text=True)
                output = run_proc.stdout.strip()
                if output == expected_output_list[i]:
                    results.append(f"✅ Test case {i+1} passed.")
                else:
                    results.append(f"❌ Test case {i+1} failed. Output: {output}, Expected: {expected_output_list[i]}")
            return "<br>".join(results)

    except Exception as e:
        return f"⚠️ Error: {str(e)}"


@pages_bp.route('/leaderboard')
@login_required
def leaderboard():
    # Fetch leaderboard data from the database
    leaderboard_data = list(db.users.find({}, {
        'rollno': 1, 
        'total_score': 1, 
        'questions_solved': 1, 
        'success_rate': 1, 
        'last_active': 1
    }).sort('total_score', -1).limit(20))  # Top 20 users

    for user in leaderboard_data:
        user['success_rate'] = round(user.get('success_rate', 0) * 100, 2)  # Convert to percentage

    return render_template('leaderboard.html', leaderboard=leaderboard_data)