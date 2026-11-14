from flask import (Flask, render_template, request, redirect,
                   send_from_directory, url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
import uuid
import os
import time
import shutil
import pymysql



def get_db_connection():
    return pymysql.connect(
        host=os.environ.get('MYSQLHOST', 'localhost'),
        user=os.environ.get('MYSQLUSER', 'root'),
        password=os.environ.get('MYSQLPASSWORD', 'Dada@9090'),
        database=os.environ.get('MYSQLDATABASE', 'plant_care_db'),
        port=int(os.environ.get('MYSQLPORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'plantcare-ai-dev-only-change-me')

os.makedirs('./uploadimages', exist_ok=True)
os.makedirs('./uploadimages/history', exist_ok=True)

# ---------- MODEL (OpenRouter-based, no TensorFlow) ----------
import base64
import requests
from PIL import Image
import io

label = [
 'Apple___Apple_scab','Apple___Black_rot','Apple___Cedar_apple_rust','Apple___healthy',
 'Background_without_leaves','Blueberry___healthy','Cherry___Powdery_mildew','Cherry___healthy',
 'Corn___Cercospora_leaf_spot Gray_leaf_spot','Corn___Common_rust','Corn___Northern_Leaf_Blight',
 'Corn___healthy','Grape___Black_rot','Grape___Esca_(Black_Measles)',
 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)','Grape___healthy',
 'Orange___Haunglongbing_(Citrus_greening)','Peach___Bacterial_spot','Peach___healthy',
 'Pepper,_bell___Bacterial_spot','Pepper,_bell___healthy','Potato___Early_blight',
 'Potato___Late_blight','Potato___healthy','Raspberry___healthy','Soybean___healthy',
 'Squash___Powdery_mildew','Strawberry___Leaf_scorch','Strawberry___healthy',
 'Tomato___Bacterial_spot','Tomato___Early_blight','Tomato___Late_blight','Tomato___Leaf_Mold',
 'Tomato___Septoria_leaf_spot','Tomato___Spider_mites Two-spotted_spider_mite',
 'Tomato___Target_Spot','Tomato___Tomato_Yellow_Leaf_Curl_Virus',
 'Tomato___Tomato_mosaic_virus','Tomato___healthy'
]

with open("plant_disease.json", 'r') as file:
    plant_disease = json.load(file)


# ---------- DECORATORS ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('overview'))
        return f(*args, **kwargs)
    return wrapper


# ---------- GLOBALS ----------
@app.context_processor
def inject_globals():
    cart = session.get('cart', {})
    return {'cart_count': sum(cart.values()) if cart else 0}


# ---------- UPLOADED IMAGES ----------
@app.route('/uploadimages/<path:filename>')
def uploaded_images(filename):
    return send_from_directory('./uploadimages', filename)


# ═══════════════════════════════════════════════════════════════
# OPENROUTER PREDICTION (replaces TensorFlow/Keras)
# ═══════════════════════════════════════════════════════════════
def model_predict(image_path):
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set!")
        return {
            "name": "Configuration Error",
            "cause": "AI service is not configured on the server.",
            "cure": "Please contact the administrator to set OPENROUTER_API_KEY."
        }

    try:
        # Image → base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # OpenRouter API call
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://plantcare-ai.up.railway.app",
                "X-Title": "PlantCare AI",
            },
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Identify the plant disease in this leaf image. "
                                    "Reply ONLY with the exact disease name from the PlantVillage dataset "
                                    "(e.g., Tomato___Early_blight). Do not write any other text."
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                            }
                        ]
                    }
                ]
            },
            timeout=30
        )

        result = response.json()

        # Validate response shape
        if 'choices' not in result or not result['choices']:
            print(f"OpenRouter bad response: {result}")
            return {
                "name": "Analysis Failed",
                "cause": "AI service returned an unexpected response.",
                "cure": "Please try again in a moment."
            }

        disease_name = result['choices'][0]['message']['content'].strip()

        # Match with local JSON
        for disease in plant_disease:
            if disease['name'].lower() == disease_name.lower():
                return disease

        # Fallback if no exact match
        return {
            "name": disease_name,
            "cause": "AI detected this condition.",
            "cure": "Please consult an expert."
        }

    except Exception as e:
        print(f"OpenRouter Error: {e}")
        return {
            "name": "Analysis Failed",
            "cause": "Could not connect to AI service.",
            "cure": "Please try again later."
        }


# ═══════════════════════════════════════════════════════════════
# ENRICH PREDICTION
# ═══════════════════════════════════════════════════════════════
PREVENTION_TIPS = {
    'Fungal': [
        'Water at the base of plants — avoid wetting leaves to reduce fungal spread',
        'Ensure good air circulation by spacing plants properly',
        'Remove and destroy infected leaves immediately — do not compost them',
        'Apply fungicide preventively during humid or rainy weather',
    ],
    'Bacterial': [
        'Avoid overhead watering to prevent bacterial splashing between plants',
        'Disinfect garden tools with rubbing alcohol between cuts',
        'Remove infected plants entirely to prevent spread to healthy neighbors',
        'Use copper-based sprays early in infection for best results',
    ],
    'Viral': [
        'Control insect vectors (whiteflies, aphids) using yellow sticky traps',
        'Remove and destroy infected plants — viruses cannot be cured once inside',
        'Use certified virus-resistant seed varieties when possible',
        'Disinfect tools and wash hands frequently to avoid mechanical transmission',
    ],
    'Pest': [
        'Use yellow sticky traps to monitor pest population early',
        'Spray neem oil or insecticidal soap in the evening for best effect',
        'Encourage natural predators like ladybugs, lacewings and spiders',
        'Inspect plants every 2-3 days for early signs of infestation',
    ],
    'Healthy': [
        'Continue your current watering and fertilization routine',
        'Monitor weekly for any early signs of disease or pests',
        'Maintain proper plant spacing for good airflow',
        'Keep a plant health log to track changes over time',
    ],
    'Unknown': [
        'Isolate the affected plant from others to prevent possible spread',
        'Consult a local agronomist or plant pathologist for confirmation',
        'Take clear photos from multiple angles for expert review',
        'Check soil moisture and nutrient levels — stress can mimic disease',
    ],
}

SYMPTOMS_BY_TYPE = {
    'Fungal': [
        'Circular or irregular spots with distinct borders',
        'Powdery, fuzzy, or rusty growth on leaf surfaces',
        'Yellowing or browning of affected tissue',
        'Spots rapidly spread in humid or wet conditions',
    ],
    'Bacterial': [
        'Water-soaked spots that turn dark brown or black',
        'Yellow halos surrounding the dark spots',
        'Angular spots limited by leaf veins',
        'Rapid wilting or collapse of affected leaves',
    ],
    'Viral': [
        'Mosaic pattern — yellow and green mottled leaves',
        'Curling, distortion or cupping of new growth',
        'Stunted plant growth and reduced fruit yield',
        'Ring spots or streaking patterns on leaves',
    ],
    'Pest': [
        'Tiny pin-prick holes or stippling on leaves',
        'Fine webbing on leaf undersides',
        'Sticky honeydew or sooty black mold',
        'Visible mites, insects or eggs on inspection',
    ],
    'Healthy': [],
    'No Plant': [],
    'Disease': [
        'Abnormal discoloration of leaves',
        'Unusual spots, lesions or texture changes',
        'Premature wilting or falling of leaves',
    ],
}


def build_understanding(pred, plant, disease_short, category, severity, is_healthy, is_background):
    if is_healthy:
        return (
            f"{plant} is currently healthy with no visible signs of disease. "
            f"The leaf shows natural coloration, proper texture, and no lesions or discoloration. "
            f"Continue your current care routine — regular watering, adequate sunlight, and periodic monitoring — "
            f"to keep the plant thriving and resistant to future infections."
        )
    if is_background:
        return (
            "The uploaded image does not appear to contain a plant leaf. "
            "This could be due to a cluttered background, poor lighting, or a non-leaf object in the frame. "
            "For accurate diagnosis, please upload a clear close-up photo of a single leaf against a plain background. "
            "Natural daylight works best — avoid shadows and blurry images."
        )

    cause_text = (pred.get('cause') or '').strip()
    if cause_text and not cause_text.endswith('.'):
        cause_text += '.'

    category_context = {
        'Fungal': "Fungal pathogens thrive in humid, warm conditions and spread through airborne spores — often affecting lower leaves first.",
        'Bacterial': "Bacterial infections spread through water splashes, contaminated tools, and insects, and can rapidly devastate a crop if left untreated.",
        'Viral': "Viral diseases are typically transmitted by insect vectors like whiteflies and aphids, and once a plant is infected it cannot be cured.",
        'Pest': "Pest infestations weaken plants by feeding on sap and transmitting harmful pathogens, requiring early intervention to prevent crop loss.",
        'Disease': "This condition can gradually weaken the plant and reduce yield if left untreated.",
    }.get(category, "")

    severity_context = {
        'High': "This is classified as HIGH severity — immediate action is strongly recommended to prevent rapid spread to nearby plants.",
        'Medium': "This is classified as MEDIUM severity — early treatment and close monitoring are important to stop the infection from worsening.",
        'Low': "This is classified as LOW severity — monitoring and preventive care should keep the plant healthy.",
    }.get(severity, "")

    sentences = [
        f"{disease_short} is a plant condition affecting {plant.lower()}.",
        cause_text,
        category_context,
        severity_context,
    ]
    return " ".join(s for s in sentences if s)


def build_treatment(pred, plant, disease_short, category, severity, is_healthy, is_background):
    if is_healthy:
        return (
            f"No medical treatment is required — {plant.lower()} is in good health. "
            f"Continue your regular watering and fertilization schedule to maintain plant vigor. "
            f"Apply a preventive neem oil spray once every 2-3 weeks during humid seasons as a protective measure. "
            f"Regular inspection (weekly) will help catch any early signs before they develop into problems."
        )
    if is_background:
        return (
            "No treatment can be recommended until a clear plant image is provided. "
            "Please capture a close-up photo of the affected leaf — ideally the most damaged part — against a plain background. "
            "Ensure natural daylight, avoid shadows, and make sure the leaf occupies most of the frame. "
            "Once re-uploaded, you'll receive a complete treatment plan tailored to the detected condition."
        )

    cure_text = (pred.get('cure') or '').strip()
    if cure_text and not cure_text.endswith('.'):
        cure_text += '.'

    category_method = {
        'Fungal': (
            "Apply a recommended fungicide (copper-based or systemic) as a foliar spray, "
            "covering both upper and lower leaf surfaces thoroughly. Repeat every 5-7 days "
            "until symptoms stop spreading — typically over a 2-3 week cycle."
        ),
        'Bacterial': (
            "Spray a copper-based bactericide early in the morning or late evening to avoid leaf burn. "
            "Prune and dispose of infected leaves in sealed bags — never compost them. "
            "Repeat application every 7 days for 2-3 weeks while monitoring new growth."
        ),
        'Viral': (
            "There is no chemical cure for viral infections — focus on removing infected plants immediately to protect neighbors. "
            "Control the insect vectors (whiteflies, aphids) with yellow sticky traps and insecticidal soap. "
            "Disinfect all tools with rubbing alcohol between cuts and wash hands frequently."
        ),
        'Pest': (
            "Apply neem oil or insecticidal soap in the evening when beneficial insects are less active. "
            "Place yellow sticky traps around the plant to catch adults and monitor population. "
            "Repeat treatment every 5-7 days for 2-3 weeks until the infestation is fully cleared."
        ),
        'Disease': (
            "Apply an appropriate broad-spectrum treatment as directed on the product label. "
            "Remove affected leaves with sterilized tools and dispose of them safely. "
            "Monitor the plant daily for any new symptoms during the treatment period."
        ),
    }.get(category, "")

    severity_followup = {
        'High': (
            "Given the HIGH severity, begin treatment today and isolate the plant from healthy ones. "
            "Expect visible improvement within 7-10 days if the treatment is followed consistently."
        ),
        'Medium': (
            "For MEDIUM severity, start treatment within 24-48 hours for best results. "
            "Most plants show recovery signs within 10-14 days of consistent application."
        ),
        'Low': (
            "LOW severity — begin treatment at your earliest convenience (within 3-5 days). "
            "With proper care, the plant should recover fully within 1-2 weeks."
        ),
    }.get(severity, "")

    sentences = [cure_text, category_method, severity_followup]
    return " ".join(s for s in sentences if s)


def enrich_prediction(pred):
    name = pred.get('name', '')
    parts = name.split('___')

    plant_raw = parts[0] if len(parts) > 0 else 'Unknown'
    plant = ' '.join(plant_raw.replace('_', ' ').replace(',', ' ').split()).title()
    if plant.lower() == 'pepper bell':
        plant = 'Bell Pepper'

    disease_raw = parts[1] if len(parts) > 1 else name
    disease_short = ' '.join(
        disease_raw.replace('_', ' ').replace('(', '').replace(')', '').split()
    )
    disease_short = ' '.join(w.capitalize() if w.isupper() else w for w in disease_short.split())

    is_healthy = 'healthy' in disease_short.lower()
    is_background = 'background' in disease_short.lower() or 'without' in disease_short.lower()

    cause_lower = (pred.get('cause') or '').lower()
    if is_healthy:
        category, category_color, category_icon = 'Healthy', 'emerald', 'fa-circle-check'
    elif is_background:
        category, category_color, category_icon = 'No Plant', 'slate', 'fa-image'
    elif 'fungus' in cause_lower or 'fungal' in cause_lower:
        category, category_color, category_icon = 'Fungal', 'amber', 'fa-disease'
    elif 'bacteri' in cause_lower:
        category, category_color, category_icon = 'Bacterial', 'rose', 'fa-bacterium'
    elif 'virus' in cause_lower or 'viral' in cause_lower or 'mosaic' in cause_lower:
        category, category_color, category_icon = 'Viral', 'purple', 'fa-virus'
    elif ('mite' in cause_lower or 'insect' in cause_lower or 'pest' in cause_lower
          or 'psyllid' in cause_lower or 'whitefl' in cause_lower):
        category, category_color, category_icon = 'Pest', 'orange', 'fa-bug'
    else:
        category, category_color, category_icon = 'Disease', 'slate', 'fa-circle-question'

    d_low = disease_short.lower()
    if is_healthy or is_background:
        severity, severity_color = ('None' if is_healthy else 'N/A'), 'emerald'
    elif any(k in d_low for k in ['blight', 'rot', 'virus', 'mosaic', 'yellow leaf curl', 'greening']):
        severity, severity_color = 'High', 'rose'
    elif any(k in d_low for k in ['spot', 'mildew', 'rust', 'mold', 'scab', 'scorch', 'measles']):
        severity, severity_color = 'Medium', 'amber'
    else:
        severity, severity_color = 'Low', 'emerald'

    if is_healthy or is_background:
        spread_risk, spread_color = 'None', 'emerald'
    elif category in ['Viral', 'Pest']:
        spread_risk, spread_color = 'High', 'rose'
    elif 'blight' in d_low or 'rust' in d_low or 'mosaic' in d_low:
        spread_risk, spread_color = 'High', 'rose'
    elif category in ['Fungal', 'Bacterial']:
        spread_risk, spread_color = 'Medium', 'amber'
    else:
        spread_risk, spread_color = 'Low', 'emerald'

    if is_healthy:
        urgency = 'All Good'
    elif is_background:
        urgency = 'Retake Photo'
    elif severity == 'High':
        urgency = 'Act Now'
    elif severity == 'Medium':
        urgency = 'Treat This Week'
    else:
        urgency = 'Monitor Closely'

    if is_healthy:
        risk_score = 5
    elif is_background:
        risk_score = 0
    else:
        risk_score = {'High': 85, 'Medium': 55, 'Low': 25}.get(severity, 50)

    symptoms = SYMPTOMS_BY_TYPE.get(category, SYMPTOMS_BY_TYPE['Disease'])

    if is_healthy:
        timeline = {
            'today': ['No action needed — plant looks healthy', 'Take a clear photo for your plant journal'],
            'week': ['Monitor weekly for any new spots or changes', 'Keep watering at the base, not on leaves'],
            'ongoing': ['Continue current care routine', 'Maintain good airflow between plants'],
        }
    elif is_background:
        timeline = {
            'today': ['Take a new photo of a single leaf against plain background', 'Ensure good natural lighting'],
            'week': ['Re-upload with a clear, close-up leaf image', 'Avoid shadows and blurry photos'],
            'ongoing': ['Try capturing leaves from multiple angles', 'Focus on visible spots or lesions'],
        }
    elif severity == 'High':
        timeline = {
            'today': ['⚠️ Isolate the affected plant immediately', 'Remove visibly infected leaves/stems (seal in a bag)', 'Apply first treatment (fungicide/bactericide spray)'],
            'week': ['Reapply treatment every 5-7 days', 'Remove any newly infected parts daily', 'Avoid overhead watering completely'],
            'ongoing': ['Monitor neighboring plants for spread', 'Improve airflow — prune dense areas', 'Complete the full treatment cycle (2-3 weeks)'],
        }
    elif severity == 'Medium':
        timeline = {
            'today': ['Prune affected leaves with sterilized tools', 'Apply appropriate treatment spray'],
            'week': ['Check daily for new symptoms', 'Continue treatment every 7 days'],
            'ongoing': ['Improve air circulation around plant', 'Apply preventive spray before humid weather'],
        }
    else:
        timeline = {
            'today': ['Monitor the affected area closely', 'Take note of the exact location of symptoms'],
            'week': ['Check if symptoms spread to neighboring leaves', 'Keep the plant well-watered but not overwatered'],
            'ongoing': ['Maintain good cultural practices', 'Re-scan if symptoms worsen'],
        }

    return {
        **pred,
        'plant': plant,
        'disease_short': disease_short,
        'is_healthy': is_healthy,
        'is_background': is_background,
        'category': category,
        'category_color': category_color,
        'category_icon': category_icon,
        'severity': severity,
        'severity_color': severity_color,
        'spread_risk': spread_risk,
        'spread_color': spread_color,
        'urgency': urgency,
        'risk_score': risk_score,
        'symptoms': symptoms,
        'timeline': timeline,
        'prevention_tips': PREVENTION_TIPS.get(category, PREVENTION_TIPS['Unknown']),
        'understanding': build_understanding(pred, plant, disease_short, category, severity, is_healthy, is_background),
        'treatment': build_treatment(pred, plant, disease_short, category, severity, is_healthy, is_background),
    }


# ---------- PUBLIC PAGES ----------
@app.route('/')
def root():
    return redirect(url_for('overview'))


@app.route('/overview')
def overview():
    return render_template('about_project.html')


@app.route('/detect')
def detect():
    upload_folder = os.path.abspath('./uploadimages')
    if os.path.exists(upload_folder):
        now = time.time()
        for filename in os.listdir(upload_folder):
            if filename.startswith('temp_'):
                path = os.path.join(upload_folder, filename)
                try:
                    if now - os.path.getmtime(path) > 86400:
                        os.remove(path)
                except Exception:
                    pass
    return render_template('home.html')


@app.route('/diseases')
def diseases():
    return render_template('diseases.html')


@app.route('/tips')
def tips():
    return render_template('tips.html')


# ---------- CONTACT ----------
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    success = False
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO support_message (user_id, name, email, subject, message) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (session.get('user_id'), name, email, subject, message)
                )
            conn.commit()
            conn.close()
            success = True
        except Exception as e:
            print(f"DB Error: {e}")
    return render_template('contact.html', success=success)


# ---------- UPLOAD / DIAGNOSE ----------
@app.route('/upload/', methods=['POST', 'GET'])
def uploadimage():
    if request.method != 'POST':
        return redirect('/detect')

    image = request.files['img']
    temp_name = f"uploadimages/temp_{uuid.uuid4().hex}"
    image_path_full = f'{temp_name}_{image.filename}'
    image.save(image_path_full)

    prediction = model_predict(f'./{image_path_full}')
    prediction = enrich_prediction(prediction)

    if session.get('user_id'):
        try:
            history_name = f"diag_{uuid.uuid4().hex}_{image.filename}"
            shutil.copy(image_path_full, os.path.join('./uploadimages/history', history_name))
            history_path = f'/uploadimages/history/{history_name}'

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO diagnosis_history "
                    "(user_id, image_path, disease_name, cause, cure) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (session['user_id'], history_path,
                     prediction['name'], prediction['cause'], prediction['cure'])
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"History save error: {e}")

    recommended = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products WHERE stock > 0 ORDER BY id LIMIT 3")
            recommended = cur.fetchall()
        conn.close()
    except Exception:
        pass

    return render_template('home.html', result=True,
                           imagepath=f'/{image_path_full}',
                           prediction=prediction,
                           recommended=recommended)


# ---------- AUTH ----------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                    if cur.fetchone():
                        flash('Email already registered. Please log in.', 'warning')
                        return redirect(url_for('login'))
                    cur.execute(
                        "INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,'user')",
                        (name, email, generate_password_hash(password))
                    )
                conn.commit()
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
            finally:
                conn.close()
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email=%s", (email,))
                user = cur.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['name'] = user['name']
                session['role'] = user['role']
                flash(f"Welcome back, {user['name']}!", 'success')
                nxt = request.args.get('next')
                if nxt:
                    return redirect(nxt)
                if user['role'] == 'admin':
                    return redirect(url_for('admin'))
                return redirect(url_for('detect'))
            flash('Invalid email or password.', 'danger')
        finally:
            conn.close()
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('overview'))


# ---------- DIAGNOSIS HISTORY ----------
@app.route('/history')
@login_required
def history():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM diagnosis_history WHERE user_id=%s ORDER BY created_at DESC",
            (session['user_id'],)
        )
        records = cur.fetchall()
        cur.execute(
            "SELECT disease_name, COUNT(*) AS cnt FROM diagnosis_history "
            "WHERE user_id=%s GROUP BY disease_name ORDER BY cnt DESC LIMIT 5",
            (session['user_id'],)
        )
        top_diseases = cur.fetchall()
    conn.close()
    return render_template('history.html', records=records, top_diseases=top_diseases)


# ---------- SHOP ----------
def get_products(category=None, search=None):
    conn = get_db_connection()
    with conn.cursor() as cur:
        q = "SELECT * FROM products WHERE stock > 0"
        params = []
        if category and category != 'all':
            q += " AND category=%s"
            params.append(category)
        if search:
            q += " AND (name LIKE %s OR description LIKE %s)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY id"
        cur.execute(q, params)
        rows = cur.fetchall()
    conn.close()
    return rows


@app.route('/shop')
def shop():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    products = get_products(category, search or None)
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM products")
        categories = [r['category'] for r in cur.fetchall()]
    conn.close()
    return render_template('shop.html', products=products, categories=categories,
                           active_category=category, search=search)


# ---------- CART ----------
@app.route('/cart')
def cart():
    cart_data = session.get('cart', {})
    items, total = [], 0
    if cart_data:
        conn = get_db_connection()
        with conn.cursor() as cur:
            ph = ','.join(['%s'] * len(cart_data))
            cur.execute(f"SELECT * FROM products WHERE id IN ({ph})", list(cart_data.keys()))
            prods = {str(p['id']): p for p in cur.fetchall()}
        conn.close()
        for pid, qty in cart_data.items():
            p = prods.get(pid)
            if p:
                sub = float(p['price']) * qty
                items.append({'product': p, 'qty': qty, 'subtotal': sub})
                total += sub
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    qty = max(1, int(request.form.get('quantity', 1)))
    cart_data = session.get('cart', {})
    cart_data[str(pid)] = cart_data.get(str(pid), 0) + qty
    session['cart'] = cart_data
    flash('Added to cart!', 'success')
    return redirect(request.referrer or url_for('shop'))


@app.route('/cart/update/<int:pid>', methods=['POST'])
def update_cart(pid):
    qty = int(request.form.get('quantity', 1))
    cart_data = session.get('cart', {})
    if qty <= 0:
        cart_data.pop(str(pid), None)
    else:
        cart_data[str(pid)] = qty
    session['cart'] = cart_data
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:pid>', methods=['POST'])
def remove_from_cart(pid):
    cart_data = session.get('cart', {})
    cart_data.pop(str(pid), None)
    session['cart'] = cart_data
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_data = session.get('cart', {})
    if not cart_data:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop'))
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            ph = ','.join(['%s'] * len(cart_data))
            cur.execute(f"SELECT * FROM products WHERE id IN ({ph})", list(cart_data.keys()))
            prods = {str(p['id']): p for p in cur.fetchall()}
            total = sum(float(prods[pid]['price']) * qty
                        for pid, qty in cart_data.items() if pid in prods)
            cur.execute(
                "INSERT INTO orders (user_id, total, status) VALUES (%s,%s,'Pending')",
                (session['user_id'], total)
            )
            order_id = cur.lastrowid
            for pid, qty in cart_data.items():
                if pid in prods:
                    p = prods[pid]
                    cur.execute(
                        "INSERT INTO order_items "
                        "(order_id, product_id, product_name, quantity, price) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (order_id, p['id'], p['name'], qty, p['price'])
                    )
                    cur.execute(
                        "UPDATE products SET stock = stock - %s WHERE id = %s",
                        (qty, p['id'])
                    )
        conn.commit()
    finally:
        conn.close()
    session['cart'] = {}
    flash('Order placed successfully! 🎉', 'success')
    return redirect(url_for('orders_page'))


# ---------- ORDERS ----------
@app.route('/orders')
@login_required
def orders_page():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC",
            (session['user_id'],)
        )
        orders = cur.fetchall()
        for o in orders:
            cur.execute("SELECT * FROM order_items WHERE order_id=%s", (o['id'],))
            o['items'] = cur.fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)


# ---------- ADMIN ----------
@app.route('/admin')
@admin_required
def admin():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM users"); users_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM diagnosis_history"); diag_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM orders"); orders_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM support_message"); msg_count = cur.fetchone()['c']

        cur.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC LIMIT 10")
        recent_users = cur.fetchall()

        cur.execute("SELECT * FROM support_message ORDER BY id DESC LIMIT 15")
        messages = cur.fetchall()

        cur.execute(
            "SELECT o.*, u.name AS user_name FROM orders o "
            "JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC LIMIT 15"
        )
        orders_list = cur.fetchall()

        cur.execute(
            "SELECT disease_name, COUNT(*) AS cnt FROM diagnosis_history "
            "GROUP BY disease_name ORDER BY cnt DESC LIMIT 5"
        )
        top_diseases = cur.fetchall()
    conn.close()
    return render_template('admin.html',
                           users_count=users_count, diag_count=diag_count,
                           orders_count=orders_count, msg_count=msg_count,
                           recent_users=recent_users, messages=messages,
                           orders_list=orders_list, top_diseases=top_diseases)


@app.route('/admin/order/<int:oid>/status', methods=['POST'])
@admin_required
def admin_order_status(oid):
    status = request.form.get('status', 'Pending')
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid))
    conn.commit()
    conn.close()
    flash('Order status updated.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/message/<int:mid>/delete', methods=['POST'])
@admin_required
def admin_delete_message(mid):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM support_message WHERE id=%s", (mid,))
    conn.commit()
    conn.close()
    flash('Message deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/user/<int:uid>/delete', methods=['POST'])
@admin_required
def admin_delete_user(uid):
    if uid == session.get('user_id'):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, role FROM users WHERE id=%s", (uid,))
            user = cur.fetchone()
            if not user:
                flash('User not found.', 'warning')
                return redirect(url_for('admin'))

            if user['role'] == 'admin':
                flash('Cannot delete another admin. Demote them first.', 'danger')
                return redirect(url_for('admin'))

            cur.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id=%s)", (uid,))
            cur.execute("DELETE FROM orders WHERE user_id=%s", (uid,))
            cur.execute("DELETE FROM diagnosis_history WHERE user_id=%s", (uid,))
            cur.execute("DELETE FROM users WHERE id=%s", (uid,))

        conn.commit()
        flash(f"User '{user['name']}' ({user['email']}) deleted successfully.", 'success')
    except Exception as e:
        print(f"Delete user error: {e}")
        flash(f'Failed to delete user: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('admin'))


# ---------- LOCAL DEV ONLY ----------
# Gunicorn uses `app:app`; do NOT run with debug=True in production.
# if __name__ == "__main__":
#     app.run(debug=True)