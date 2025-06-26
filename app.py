from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from openai import OpenAI
from dotenv import load_dotenv
from datetime import timedelta
import os

# ─── LOAD ENV VARIABLES ─────────────────────────────────────────────────────────
load_dotenv()  # Load .env in project root

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing environment variable OPENAI_API_KEY")

# Instantiate OpenAI client (v1.x)
client = OpenAI(api_key=api_key)

app = Flask(__name__)
app.secret_key = "your-super-secret-key"      # Replace for production

# ── SESSION CONFIG ────────────────────────────────────
app.config.update(
  SESSION_TYPE='filesystem',
  SESSION_PERMANENT=True,
  PERMANENT_SESSION_LIFETIME=timedelta(days=365),
  SESSION_COOKIE_SAMESITE='Lax',    # or 'None'
  SESSION_COOKIE_SECURE=False       # set True in prod over HTTPS
)
Session(app)

@app.before_request
def refresh_session():
    session.permanent = True

# ─── IPIP-50 QUESTIONS LIST ─────────────────────────────────────────────────────
QUESTIONS = [
    ("extraversion", "Am the life of the party.", False),
    ("agreeableness", "Feel little concern for others.", True),
    ("conscientiousness", "Am always prepared.", False),
    ("neuroticism", "Get stressed out easily.", False),
    ("openness", "Have a rich vocabulary.", False),
    ("extraversion", "Don't talk a lot.", True),
    ("agreeableness", "Am interested in people.", False),
    ("conscientiousness", "Leave my belongings around.", True),
    ("neuroticism", "Am relaxed most of the time.", True),
    ("openness", "Have difficulty understanding abstract ideas.", True),
    ("extraversion", "Feel comfortable around people.", False),
    ("agreeableness", "Insult people.", True),
    ("conscientiousness", "Pay attention to details.", False),
    ("neuroticism", "Worry about things.", False),
    ("openness", "Have a vivid imagination.", False),
    ("extraversion", "Keep in the background.", True),
    ("agreeableness", "Sympathize with others' feelings.", False),
    ("conscientiousness", "Make a mess of things.", True),
    ("neuroticism", "Seldom feel blue.", True),
    ("openness", "Am not interested in abstract ideas.", True),
    ("extraversion", "Start conversations.", False),
    ("agreeableness", "Am not interested in other people's problems.", True),
    ("conscientiousness", "Get chores done right away.", False),
    ("neuroticism", "Am easily disturbed.", False),
    ("openness", "Have excellent ideas.", False),
    ("extraversion", "Have little to say.", True),
    ("agreeableness", "Have a soft heart.", False),
    ("conscientiousness", "Often forget to put things back in their proper place.", True),
    ("neuroticism", "Get upset easily.", False),
    ("openness", "Do not have a good imagination.", True),
    ("extraversion", "Talk to a lot of different people at parties.", False),
    ("agreeableness", "Am not really interested in others.", True),
    ("conscientiousness", "Like order.", False),
    ("neuroticism", "Change my mood a lot.", False),
    ("openness", "Am quick to understand things.", False),
    ("extraversion", "Don't like to draw attention to myself.", True),
    ("agreeableness", "Take time out for others.", False),
    ("conscientiousness", "Shirk my duties.", True),
    ("neuroticism", "Have frequent mood swings.", False),
    ("openness", "Use difficult words.", False),
    ("extraversion", "Don't mind being the center of attention.", False),
    ("agreeableness", "Feel others' emotions.", False),
    ("conscientiousness", "Follow a schedule.", False),
    ("neuroticism", "Get irritated easily.", False),
    ("openness", "Spend time reflecting on things.", False),
    ("extraversion", "Am quiet around strangers.", True),
    ("agreeableness", "Make people feel at ease.", False),
    ("conscientiousness", "Am exacting in my work.", False),
    ("neuroticism", "Often feel blue.", False),
    ("openness", "Am full of ideas.", False),
]

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────────
def compute_scores(answer_list):
    sums = {trait: 0 for trait, _, _ in QUESTIONS}
    counts = {trait: 0 for trait, _, _ in QUESTIONS}
    for trait, val, rev in answer_list:
        score = (6 - val) if rev else val
        sums[trait] += score
        counts[trait] += 1
    return {trait: round(sums[trait] / counts[trait], 2)
            for trait in sums if counts[trait]}

def generate_report(scores):
    prompt = (
        "Write a detailed Big Five personality report in the style of Jordan Peterson. "
        "For each trait (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism), "
        "create a separate paragraph of about 130 words, starting with the trait name in bold (e.g. **Openness:**). "
        "After those five paragraphs, add a final concluding paragraph with actionable insights for self-development. "
        f"The numeric scores are: {scores}. Use academic research tone, referencing general psychological concepts."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a psychology professor with a writing style similar to Jordan Peterson."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content

# ─── FLASK ROUTES ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    session.clear()
    session['phase'] = 'welcome'
    session['answers'] = []
    session['q_index'] = 0
    return render_template('chat.html')

@app.route('/start', methods=['GET'])
def start():
    session['phase'] = 'consent'
    welcome = "🌟 Welcome to the Story-Based Personality Chatbot! 🌟"
    purpose = (
        "We are conducting a research study to measure Big Five personality traits using the IPIP-50 scale. "
        "You will answer 50 statements about yourself, each on a scale of 1 (Very Inaccurate) to 5 (Very Accurate). "
        "Your responses will help us better understand personality structure.\n\n"
    )
    participation = (
        "Participation is completely voluntary. You can stop at any time without penalty. "
        "There is minimal risk: you may feel some self-reflection while answering. "
        "There is no direct benefit to you, but your data will help advance psychological research.\n\n"
    )
    confidentiality = (
        "All responses are anonymous and stored securely on an encrypted server. "
        "No personally identifying information will be linked to your answers. "
        "Data will be reported only in aggregate.\n\n"
    )
    irb = (
        "This study has been approved by the University of Sunderland. "
        "If you have questions about your rights, contact the University. "
        "For study-related queries, contact Allison.\n\n"
    )
    consent = (
        "Do you consent to participate under these terms? "
        "(Type 'I consent' to proceed or 'I do not consent' to exit.)"
    )
    full_reply = welcome + "\n\n" + purpose + participation + confidentiality + irb + consent
    return jsonify({"reply": full_reply})

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '').strip()
    phase = session.get('phase', '')

    # Consent phase
    if phase == 'consent':
        msg = user_message.lower().strip().rstrip('.')
        if msg in ['i consent', 'yes', 'y', 'consent']:
            session['phase'] = 'ask_age'
            return jsonify({"reply": "Great! First, what is your age in years? (Please enter a number, e.g., 25)"})
        else:
            return jsonify({"reply": "Understood. Thank you for your time. You may close this window."})

    # Ask Age
    if phase == 'ask_age':
        if not user_message.isdigit():
            return jsonify({"reply": "Please enter your age as a number (e.g., 25)."})
        age = int(user_message)
        if age < 18:
            return jsonify({"reply": "Sorry, you must be 18 or older to participate. Thank you for your interest."})
        session['demographics'] = {"age": age}
        session['phase'] = 'ask_country'
        return jsonify({"reply": "Thanks. Next, which country do you live in?"})

    # Ask Country
    if phase == 'ask_country':
        country = user_message
        if not country:
            return jsonify({"reply": "Please type the name of your country."})
        session['demographics']["country"] = country
        session['phase'] = 'ask_education'
        return jsonify({"reply": "Got it. Finally, what is your highest education level?"})

    # Ask Education
    if phase == 'ask_education':
        education = user_message
        if not education:
            return jsonify({"reply": "Please specify your highest education level."})
        session['demographics']["education"] = education
        session['phase'] = 'comprehension'
        return jsonify({"reply": "Quick check: True or False: You can withdraw at any time without penalty."})

    # Comprehension
    if phase == 'comprehension':
        if user_message.lower() in ['true', 't', 'true.']:
            session['phase'] = 'questions'
            session['q_index'] = 1
            return jsonify({"reply": f"Excellent. Question 1/50: {QUESTIONS[0][1]} (1–5)"} )
        else:
            return jsonify({"reply": "Please respond 'True' to proceed."})

    # IPIP-50 Questions
    if phase == 'questions':
        q_index = session.get('q_index', 0)
        total = len(QUESTIONS)
        if 1 <= q_index <= total:
            try:
                val = int(user_message)
                if not 1 <= val <= 5:
                    raise ValueError
            except ValueError:
                return jsonify({"reply": "Answer with a number between 1 and 5."})
            trait, _, rev = QUESTIONS[q_index-1]
            session['answers'].append((trait, val, rev))

        if q_index < total:
            session['q_index'] = q_index + 1
            return jsonify({"reply": f"Question {q_index+1}/{total}: {QUESTIONS[q_index][1]} (1–5)"} )
        # done
        session['phase'] = 'report'
        session['report'] = generate_report(compute_scores(session['answers']))
        return jsonify({"reply": "That was the last question! Generating your report…", "report_ready": True})

    # Deliver report
    if phase == 'report':
        report = session.pop('report', "Error generating report.")
        session.clear()
        return jsonify({"reply": report})

    # fallback
    return jsonify({"reply": "Unexpected input. Please refresh to restart."})

if __name__ == "__main__":
    app.run(debug=True)
