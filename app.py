import os
from urllib import response
from dotenv import load_dotenv
from groq import Groq
from flask import Flask, render_template, request, session, redirect, url_for
from auth import auth
from database import create_tables, get_db
from plagiarism import jaccard_similarity, combined_similarity

load_dotenv()
# Keep all of this exactly as is
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def generate_with_fallback(prompt):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content, None 
            except Exception as e:
                return None, f"Error calling AI model:{e}"


app = Flask(__name__)
app.jinja_env.globals.update(enumerate=enumerate)
app.secret_key = "supersecretkey"
app.register_blueprint(auth)
create_tables()


@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/demo', methods=['GET', 'POST'])
def demo():
    result = None

    if request.method == 'POST':
        code1 = request.form.get('code1')
        code2 = request.form.get('code2')
        language = request.form['language']

        if code1 and code2:
            result = combined_similarity(code1, code2)

        elif code1:
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))

            conn = get_db()
            cursor = conn.cursor()
            current_user_id = session['user_id']

            cursor.execute(
                "SELECT code_text FROM stored_codes WHERE language = ? AND user_id != ?",
                (language, current_user_id)
            )
            previous_codes = cursor.fetchall()

            highest_similarity = 0
            for row in previous_codes:
                stored_code = row["code_text"]
                similarity = combined_similarity(code1, stored_code)
                if similarity > highest_similarity:
                    highest_similarity = similarity

            cursor.execute(
                """INSERT INTO stored_codes
                (code_text, user_id, similarity, language)
                VALUES (?, ?, ?, ?)""",
                (code1, session['user_id'], highest_similarity, language)
            )
            conn.commit()
            conn.close()
            result = highest_similarity

    return render_template('demo.html', result=result)


@app.route("/code-summary", methods=["GET", "POST"])
def code_summary():
    explanation = None
    problems = None
    corrected_code = None

    if request.method == "POST":
        user_code = request.form.get("code")
        language = request.form.get("language", "python")

        if user_code:
            prompt = f"""You are a code assistant. Analyze this {language} code and respond in this exact format:

WHAT IT DOES:
[1-3 sentences max. Plain English. No jargon.]

ISSUES:
[List only real bugs or errors. If none, write "None found." Use short bullet points.]

CORRECTED CODE:
[Only include if there are bugs. Otherwise write "No changes needed."]

Code to analyze:
{user_code}

Keep everything short and direct. No long explanations."""

            try:
                raw, error = generate_with_fallback(prompt)
                if error:
                    raise Exception(error)
                raw = raw.strip()    

                def extract_section(text, header, next_headers):
                    start = text.find(header)
                    if start == -1:
                        return None
                    start += len(header)
                    end = len(text)
                    for h in next_headers:
                        pos = text.find(h, start)
                        if pos != -1 and pos < end:
                            end = pos
                    return text[start:end].strip()

                explanation    = extract_section(raw, "WHAT IT DOES:", ["ISSUES:", "CORRECTED CODE:"])
                problems       = extract_section(raw, "ISSUES:", ["CORRECTED CODE:"])
                corrected_code = extract_section(raw, "CORRECTED CODE:", [])

                def clean(text):
                    if not text:
                        return None
                    text = text.replace("```python", "").replace("```", "").strip()
                    return text if text not in ["No changes needed.", "None found."] else None

                explanation    = clean(explanation)
                problems       = clean(problems)
                corrected_code = clean(corrected_code)

            except Exception as e:
                problems = f"Error calling Gemini API: {e}"

    return render_template(
        "code_summary.html",
        explanation=explanation,
        problems=problems,
        corrected_code=corrected_code
    )


@app.route("/code-quiz", methods=["GET", "POST"])
def code_quiz():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # ✅ Always define these at the top — fixes unbound local error
    quiz_data = None
    error = None

    if request.method == "POST":
        user_code = request.form.get("code")
        language = request.form.get("language", "python")

        if user_code:
            prompt = f"""You are a coding quiz generator. Analyze this {language} code and generate exactly 5 multiple choice questions to test comprehension.

Respond ONLY with valid JSON. No explanation, no markdown, no extra text. Just the JSON.

Format:
{{
  "questions": [
    {{
      "question": "What does this code do?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "A"
    }}
  ]
}}

Rules:
- Questions must be specifically about THIS code, not general knowledge
- One correct answer per question
- answer field must be exactly "A", "B", "C", or "D"
- Make questions test real understanding, not just variable names

Code to analyze:
{user_code}"""

            try:
                raw, error = generate_with_fallback(prompt)
                if error:
                    raise Exception(error)
                raw = raw.strip()                   
                raw = raw.replace("```json", "").replace("```", "").strip()

                import json
                quiz_data = json.loads(raw)

            except Exception as e:
                error = f"Error generating quiz: {e}"

    return render_template("code_quiz.html", quiz_data=quiz_data, error=error)


@app.route("/code-converter", methods=["GET", "POST"])
def code_converter():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # ✅ Always define these at the top — fixes unbound local error
    converted_code = None
    explanation = None
    error = None

    if request.method == "POST":
        user_code = request.form.get("code")
        source_lang = request.form.get("source_language", "python")
        target_lang = request.form.get("target_language", "javascript")

        if user_code:
            prompt = f"""You are a code converter. Convert the following {source_lang} code to {target_lang}.

Respond in this EXACT format and nothing else:

CONVERTED CODE:
[the converted {target_lang} code here]

WHAT CHANGED:
[2-4 bullet points max explaining the key differences. Plain English. Keep it short.]

Rules:
- Preserve the exact same logic and output
- Use proper {target_lang} conventions and syntax
- Do not add extra features or change what the code does
- WHAT CHANGED section should only mention meaningful differences, not obvious ones

Code to convert:
{user_code}"""

            try:
                raw, error = generate_with_fallback(prompt)
                if error:
                    raise Exception(error)
                raw = raw.strip()

                def extract_section(text, header, next_headers):
                    start = text.find(header)
                    if start == -1:
                        return None
                    start += len(header)
                    end = len(text)
                    for h in next_headers:
                        pos = text.find(h, start)
                        if pos != -1 and pos < end:
                            end = pos
                    return text[start:end].strip()

                converted_code = extract_section(raw, "CONVERTED CODE:", ["WHAT CHANGED:"])
                explanation    = extract_section(raw, "WHAT CHANGED:", [])

                if converted_code:
                    converted_code = converted_code.replace("```javascript", "").replace("```java", "")
                    converted_code = converted_code.replace("```python", "").replace("```cpp", "")
                    converted_code = converted_code.replace("```", "").strip()

            except Exception as e:
                error = f"Error calling Model API: {e}"

    return render_template(
        "code_converter.html",
        converted_code=converted_code,
        explanation=explanation,
        error=error
    )


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) as total FROM stored_codes WHERE user_id = ?",
        (session['user_id'],)
    )
    total_checks = cursor.fetchone()['total']

    cursor.execute(
        """SELECT similarity, language, created_at
           FROM stored_codes WHERE user_id = ?
           ORDER BY created_at DESC LIMIT 5""",
        (session['user_id'],)
    )
    recent_checks = cursor.fetchall()
    conn.close()

    return render_template(
        'dashboard.html',
        user=user,
        total_checks=total_checks,
        recent_checks=recent_checks
    )


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)