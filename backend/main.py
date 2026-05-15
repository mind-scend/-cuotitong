import os, json, uuid, hashlib, time
from datetime import datetime, timedelta
from functools import wraps

import jwt
import requests
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
import pdfkit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-123456')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///smart_errors.db')
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'your-api-key')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
DEEPSEEK_MODEL = 'deepseek-chat'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(128))
    is_member = db.Column(db.Boolean, default=False)
    errors = db.relationship('ErrorRecord', backref='user')

class ErrorRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(20), default='math')
    clean_question = db.Column(db.Text)
    error_steps = db.Column(db.Text)
    error_reason = db.Column(db.Text)
    error_type = db.Column(db.String(50))
    knowledge_path = db.Column(db.Text)
    variants = db.Column(db.Text)
    review_count = db.Column(db.Integer, default=0)
    next_review = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

def call_llm(prompt, img_path=None, temperature=0.3):
    import base64
    messages = []
    if img_path:
        with open(img_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        })
    else:
        messages.append({"role": "user", "content": prompt})
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    resp = requests.post(DEEPSEEK_API_URL, json={
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature
    }, headers=headers)
    return resp.json()['choices'][0]['message']['content']

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "请先登录"}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user = User.query.get(data['user_id'])
        except:
            return jsonify({"error": "登录已过期"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "用户名已存在"}), 400
    user = User(
        username=data['username'],
        password_hash=hashlib.sha256(data['password'].encode()).hexdigest()
    )
    db.session.add(user); db.session.commit()
    token = jwt.encode({'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)}, app.config['SECRET_KEY'])
    return jsonify({"token": token, "user_id": user.id})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if not user or user.password_hash != hashlib.sha256(data['password'].encode()).hexdigest():
        return jsonify({"error": "用户名或密码错误"}), 401
    token = jwt.encode({'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)}, app.config['SECRET_KEY'])
    return jsonify({"token": token, "is_member": user.is_member})

@app.route('/api/analyze', methods=['POST'])
@token_required
def analyze_mistake():
    file = request.files.get('image')
    if not file:
        return jsonify({"error": "请上传图片"}), 400
    filename = secure_filename(f"{uuid.uuid4()}.jpg")
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(img_path)
    subject = request.form.get('subject', 'math')

    prompt1 = """提取图片中的数学题和学生手写解答。严格返回JSON: {"clean_question":"...", "wrong_steps":["...","..."], "error_step_index":1, "error_reason":"..."}"""
    res1 = json.loads(call_llm(prompt1, img_path))
    clean_q = res1['clean_question']
    steps = res1['wrong_steps'][res1['error_step_index']-1:] if res1['error_step_index'] > 0 else []
    prompt2 = f"""题目: {clean_q}\n错误步骤: {steps}\n判断错误类型(计算/概念/审题/步骤跳步/其他)，给出知识溯源路径和正确答案步骤。返回JSON: {{"error_type":"...", "knowledge_path":"...", "correct_solution":"..."}}"""
    res2 = json.loads(call_llm(prompt2))
    prompt3 = f"""原题: {clean_q}\n错因: {res1['error_reason']}\n生成三道变式题。返回JSON: {{"basic":{{"question":"","answer":"","hint":""}}, "medium":{{...}}, "hard":{{...}}}}"""
    variants = json.loads(call_llm(prompt3, temperature=0.8))

    record = ErrorRecord(
        user_id=request.user.id,
        subject=subject,
        clean_question=clean_q,
        error_steps=json.dumps(res1['wrong_steps']),
        error_reason=res1['error_reason'],
        error_type=res2['error_type'],
        knowledge_path=res2['knowledge_path'],
        variants=json.dumps(variants)
    )
    db.session.add(record); db.session.commit()
    return jsonify({
        "record_id": record.id,
        "clean_question": clean_q,
        "error_reason": res1['error_reason'],
        "error_type": res2['error_type'],
        "knowledge_path": res2['knowledge_path'],
        "correct_solution": res2['correct_solution'],
        "variants": variants
    })

@app.route('/api/reviews/today', methods=['GET'])
@token_required
def get_today_reviews():
    now = datetime.now()
    records = ErrorRecord.query.filter(
        ErrorRecord.user_id == request.user.id,
        ErrorRecord.next_review <= now
    ).all()
    return jsonify([{
        "id": r.id, "subject": r.subject, "question": r.clean_question,
        "error_type": r.error_type, "variants": json.loads(r.variants)
    } for r in records])

@app.route('/api/review/<int:record_id>/done', methods=['POST'])
@token_required
def mark_review_done(record_id):
    record = ErrorRecord.query.get(record_id)
    intervals = [1, 2, 4, 7, 15, 30]
    if record.review_count < len(intervals) - 1:
        record.review_count += 1
        record.next_review = datetime.now() + timedelta(days=intervals[record.review_count])
    else:
        record.next_review = datetime.max
    db.session.commit()
    return jsonify({"message": "OK"})

@app.route('/api/export_paper', methods=['POST'])
@token_required
def export_paper():
    data = request.get_json()
    record_ids = data.get('record_ids', [])
    records = ErrorRecord.query.filter(ErrorRecord.id.in_(record_ids)).all()
    html = "<h2>错题重做卷</h2>"
    for i, r in enumerate(records):
        html += f"<p><b>{i+1}. {r.clean_question}</b></p>"
        vars = json.loads(r.variants)
        html += f"<p>变式巩固：{vars['basic']['question']}</p><hr>"
    pdf_path = f"papers/{uuid.uuid4()}.pdf"
    pdfkit.from_string(html, pdf_path)
    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('papers', exist_ok=True)
    app.run(debug=True, port=5000)
