from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
import os
import time
from werkzeug.utils import secure_filename

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
session_thread_id = None

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global session_thread_id
    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'error': 'No selected file'})

    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    uploaded_file.save(file_path)

    if not session_thread_id:
        thread = openai.beta.threads.create()
        session_thread_id = thread.id

    with open(file_path, "rb") as f:
        image_file = openai.files.create(file=f, purpose="vision")

    message = openai.beta.threads.messages.create(
        thread_id=session_thread_id,
        role="user",
        content="Bitte analysiere dieses Kleidungsstück und generiere daraus einen hochwertigen Prompt für ein Modefoto.",
        file_ids=[image_file.id]
    )

    run = openai.beta.threads.runs.create(
        assistant_id=ASSISTANT_ID,
        thread_id=session_thread_id
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(
            thread_id=session_thread_id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break
        time.sleep(1)

    messages = openai.beta.threads.messages.list(thread_id=session_thread_id)
    reply = messages.data[0].content[0].text.value

    dalle_response = openai.images.generate(
        model="dall-e-3",
        prompt=reply,
        size="1024x1024",
        quality="standard",
        n=1
    )
    image_url = dalle_response.data[0].url
app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
