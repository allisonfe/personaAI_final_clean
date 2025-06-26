from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from openai import OpenAI
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import timedelta
import redis
import os

# ─── LOAD ENV VARIABLES ─────────────────────────────────────────────────────────
load_dotenv()  # Load .env in project root

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Variável de ambiente OPENAI_API_KEY ausente")

# Instancia o cliente OpenAI
client = OpenAI(api_key=api_key)

redis_url = os.environ.get('REDIS_URL')

r = redis.Redis.from_url(redis_url)
r.set("foo", "bar")
value = r.get("foo")
print(value.decode())

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://preview--persona-path-unlocked.lovable.app/"])

app.secret_key = os.getenv("SECRET_KEY")

# ── CONFIGURAÇÃO DE SESSÃO ──────────────────────────────────────────────────────
app.config.update(
  SESSION_TYPE='redis',
  SESSION_REDIS=redis.from_url(os.environ['REDIS_URL']),
  SESSION_PERMANENT=True,
  PERMANENT_SESSION_LIFETIME=timedelta(days=365),
  SESSION_COOKIE_SAMESITE='None',
  SESSION_COOKIE_SECURE=True,
  SESSION_USE_SIGNER=True
)
Session(app)

@app.before_request
def refresh_session():
    session.permanent = True

# ─── IPIP-50 QUESTIONS LIST ─────────────────────────────────────────────────────
QUESTIONS = [
# The complete list of 50 elaborative, translated Big Five personality questions
# Each tuple follows the format: (trait, elaborative_english, elaborative_portuguese, reversed)
    ("extraversion", "Quando estou em eventos sociais, costumo chamar a atenção, faço piadas e animo as pessoas ao meu redor — realmente gosto de estar no centro das atenções.", False),
    ("agreeableness", "Raramente me sinto preocupado ou envolvido emocionalmente quando os outros falam sobre seus problemas — costumo permanecer indiferente.", True),
    ("conscientiousness", "Sempre planejo com antecedência e me certifico de estar preparado para qualquer tarefa ou compromisso que surja.", False),
    ("neuroticism", "Até mesmo pequenos problemas podem me sobrecarregar — fico estressado com facilidade e frequentemente me sinto ansioso.", False),
    ("openness", "Gosto de aprender novas palavras e usar um vocabulário rico e expressivo nas minhas conversas e na escrita.", False),
    ("extraversion", "Costumo guardar minhas palavras em conversas e prefiro não falar muito quando estou com outras pessoas.", True),
    ("agreeableness", "Tenho um interesse genuíno em conhecer as pessoas e entender o que é importante para elas.", False),
    ("conscientiousness", "Costumo deixar minhas coisas espalhadas e geralmente não me esforço para manter meu espaço organizado.", True),
    ("neuroticism", "Na maioria das vezes, me sinto calmo e tranquilo, mesmo quando as coisas não saem como planejado.", True),
    ("openness", "Tenho dificuldade em entender teorias abstratas ou ideias complexas que não sejam concretas ou práticas.", True),
    ("extraversion", "Me sinto confortável e confiante quando estou com outras pessoas, mesmo em grupos grandes ou em ambientes novos.", False),
    ("agreeableness", "Às vezes digo coisas ofensivas sem me importar muito com como elas vão afetar os outros.", True),
    ("conscientiousness", "Sou atento aos detalhes e percebo pequenas coisas que outros geralmente não notam — tenho orgulho da minha precisão.", False),
    ("neuroticism", "É comum eu me preocupar com as coisas, mesmo quando elas parecem estar sob controle para os outros.", False),
    ("openness", "Frequentemente visualizo cenários criativos, incomuns ou imaginários — minha imaginação é muito ativa.", False),
    ("extraversion", "Em situações em grupo, geralmente fico em segundo plano e deixo que os outros liderem nas falas ou ações.", True),
    ("agreeableness", "Naturalmente empatizo com os outros e sinto suas emoções profundamente — a dor deles me afeta.", False),
    ("conscientiousness", "Tendo a bagunçar as coisas e tenho dificuldade em manter tarefas e objetos organizados.", True),
    ("neuroticism", "Raramente me sinto para baixo ou emocionalmente abalado — meu humor geralmente permanece estável.", True),
    ("openness", "Acho ideias abstratas ou filosóficas pouco interessantes e difíceis de acompanhar.", True),
    ("extraversion", "Geralmente sou eu quem quebra o silêncio e inicia as conversas.", False),
    ("agreeableness", "Não me sinto motivado a ajudar os outros com seus conflitos emocionais — mantenho distância.", True),
    ("conscientiousness", "Não deixo as coisas para depois — costumo concluir tarefas imediatamente, sem atraso.", False),
    ("neuroticism", "Mesmo pequenas interrupções podem me deixar desconfortável ou emocionalmente abalado.", False),
    ("openness", "Sou cheio de ideias inovadoras e práticas que surgem facilmente para mim.", False),
    ("extraversion", "Quando estou com outras pessoas, geralmente não tenho muito a dizer — fico quieto a menos que me perguntem algo.", True),
    ("agreeableness", "Me importo profundamente com os outros e frequentemente sinto carinho e compaixão por eles.", False),
    ("conscientiousness", "Frequentemente esqueço de devolver coisas ao seu lugar ou de completar pequenas tarefas.", True),
    ("neuroticism", "Minhas emoções raramente se intensificam rapidamente — mantenho os pés no chão mesmo quando as coisas dão errado.", False),
    ("openness", "Tenho dificuldade em criar ideias novas ou originais — criatividade não é meu ponto forte.", True),
    ("extraversion", "Gosto de interagir com várias pessoas diferentes em festas e me movimento entre os grupos com facilidade.", False),
    ("agreeableness", "Costumo não ser muito curioso sobre os outros ou sobre o que está acontecendo na vida deles.", True),
    ("conscientiousness", "Gosto de ter um ambiente limpo e estruturado — a ordem me ajuda a me sentir no controle.", False),
    ("neuroticism", "Meu humor tende a mudar rapidamente e com frequência — posso passar de calmo a irritado com facilidade.", False),
    ("openness", "Geralmente entendo novos conceitos e ideias complexas com bastante facilidade.", False),
    ("extraversion", "Evito situações em que toda a atenção está em mim — prefiro passar despercebido.", True),
    ("agreeableness", "Tiro tempo do meu dia para apoiar e cuidar dos outros, mesmo quando é inconveniente.", False),
    ("conscientiousness", "Costumo evitar responsabilidades e adiar ou ignorar deveres quando posso.", True),
    ("neuroticism", "Frequentemente experimento mudanças emocionais intensas que podem acontecer sem aviso.", False),
    ("openness", "Naturalmente uso palavras sofisticadas ou acadêmicas ao me expressar.", False),
    ("extraversion", "Me sinto totalmente confortável em estar no centro das atenções e gosto de ter a atenção das pessoas.", False),
    ("agreeableness", "Consigo facilmente perceber como os outros estão se sentindo — as emoções deles me afetam profundamente.", False),
    ("conscientiousness", "Sigo uma rotina ou cronograma e prefiro estrutura à espontaneidade.", False),
    ("neuroticism", "Posso ficar irritado ou frustrado com facilidade, mesmo com coisas pequenas.", False),
    ("openness", "Frequentemente passo tempo pensando sobre ideias, a vida ou o futuro — reflito profundamente.", False),
    ("extraversion", "Costumo ser quieto e reservado quando conheço novas pessoas ou entro em lugares desconhecidos.", True),
    ("agreeableness", "Tento fazer com que os outros se sintam bem-vindos, compreendidos e confortáveis quando estão comigo.", False),
    ("conscientiousness", "Exijo muito de mim mesmo e cobro precisão no trabalho que faço.", False),
    ("neuroticism", "É raro eu me sentir profundamente triste ou emocionalmente sobrecarregado por longos períodos.", False),
    ("openness", "Estou constantemente imaginando coisas, criando conceitos ou invenções na minha mente.", False),
]


# This is now a list of Python tuples ready to be used for scoring, database, or questionnaire logic.


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
    prompt = (   "Escreva um relatório detalhado da personalidade Big Five no estilo de Jordan Peterson. "
        "Para cada traço (Abertura, Conscienciosidade, Extroversão, Amabilidade, Neuroticismo), "
        "crie um parágrafo de cerca de 130 palavras, começando com o nome do traço em negrito (por exemplo, **Abertura:**). "
        "Após esses cinco parágrafos, adicione um parágrafo final com sugestões práticas para o autodesenvolvimento. "
        f"As pontuações numéricas são: {scores}. Use um tom acadêmico com base em conceitos psicológicos."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um professor de psicologia com estilo de escrita semelhante a Jordan Peterson."},
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
    welcome = " Bem-vindo(a) ao Chatbot de Personalidade com Base em Histórias! "
    purpose = (
        "Este é um teste de personalidade baseado na escala IPIP-50 (International Personality Item Pool), "
        "uma ferramenta validada e confiável usada em pesquisas psicológicas para avaliar os traços da personalidade "
        "conhecidos como os Cinco Grandes (Big Five).\n\n"
    )
    adaptation = (
        "As afirmações do teste foram adaptadas para um formato de conversa com elementos narrativos, "
        "a fim de tornar a experiência mais pessoal e envolvente.\n\n"
    )
    disclaimer = (
        " Importante: Esta ferramenta **não é um instrumento médico ou diagnóstico**. "
        "Ela **não substitui uma avaliação psicológica realizada por um(a) psicólogo(a) qualificado(a)**. "
        "Os resultados devem ser utilizados apenas para fins de **autoconhecimento e desenvolvimento pessoal**.\n\n"
    )
    ethics = (
        "Sua participação é completamente voluntária. Você pode parar a qualquer momento, sem penalidades. "
        "Não há riscos significativos, mas você pode experimentar momentos de reflexão ao responder às perguntas. "
        "Nenhuma informação pessoal identificável será coletada. Seus dados são anônimos, armazenados de forma segura "
        "e utilizados apenas de maneira agregada para fins educacionais e de desenvolvimento pessoal.\n\n"
    )
    rights = (
        "Este projeto é inspirado por práticas baseadas em evidências e foi criado com responsabilidade ética. "
        "Caso tenha dúvidas, sinta-se à vontade para entrar em contato com a criadora, Allison.\n\n"
    )
    consent = (
        "Você consente em participar com base nestas informações? "
        "(Digite 'Eu concordo' para continuar ou 'Não concordo' para encerrar.)"
    )
    full_reply = welcome + "\n\n" + purpose + adaptation + disclaimer + ethics + rights + consent
    return jsonify({"reply": full_reply})


@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    phase = session.get("phase", "consent")

    # Consent phase
    if phase == 'consent':
        msg = user_message.lower().strip().rstrip('.')
        if msg in ['eu concordo', 'sim', 'concordo']:
            session['phase'] = 'ask_age'
            return jsonify({"reply": "Ótimo! Primeiro, qual é a sua idade em anos? (Digite um número, por exemplo: 25)"})
        else:
            return jsonify({"reply": "Entendido. Obrigado pelo seu tempo. Você pode fechar esta janela."})

    # Ask Age
    if phase == 'ask_age':
        if not user_message.isdigit():
            return jsonify({"reply": "Por favor, digite sua idade como um número (ex: 25)."})
        age = int(user_message)
        if age < 18:
            return jsonify({"reply": "Desculpe, você precisa ter 18 anos ou mais para participar. Obrigado pelo seu interesse."})
        session['demographics'] = {"age": age}
        session['phase'] = 'ask_country'
        return jsonify({"reply": "Obrigado. Agora, em qual país você mora?"})

    # Ask Country
    if phase == 'ask_country':
        country = user_message
        if not country:
            return jsonify({"reply": "Por favor, digite o nome do seu país."})
        session['demographics']["country"] = country
        session['phase'] = 'ask_education'
        return jsonify({"reply": "Certo. Por fim, qual é o seu nível mais alto de escolaridade?"})

    # Ask Education
    if phase == 'ask_education':
        education = user_message
        if not education:
            return jsonify({"reply": "Por favor, informe seu nível de escolaridade mais alto."})
        session['demographics']["education"] = education
        session['phase'] = 'comprehension'
        return jsonify({"reply": "Rápido teste: Verdadeiro ou Falso: Você pode sair a qualquer momento sem penalidades."})

    # Comprehension check
    if phase == 'comprehension':
        if user_message.lower() in ['verdadeiro', 'v', 'verdadeiro.']:
            session['phase'] = 'questions'
            session['q_index'] = 1
            return jsonify({"reply": f"Excelente. Pergunta 1/50: {QUESTIONS[0][1]} (1–5)"})
        else:
            return jsonify({"reply": "Por favor, responda 'Verdadeiro' para continuar."})

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
