# routes/pages.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
import subprocess
import tempfile
import os

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


@pages_bp.route('/quiz', methods=['GET'])
@login_required
def quiz():
    return render_template('quiz.html')


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

