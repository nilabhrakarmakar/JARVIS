from flask import Flask, render_template, request, jsonify
from duckduckgo_search import DDGS
from groq import Groq
import os
import psutil
import PyPDF2 
import base64 

app = Flask(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MULTI-USER MEMORY (EMAIL BASED SECURITY) ---
user_sessions = {} 

def load_brain(email):
    filename = f"brain_{email}.txt"
    try:
        if not os.path.exists(filename):
            open(filename, 'w').close()
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception:
        return ""

def update_brain(email, new_fact):
    filename = f"brain_{email}.txt"
    try:
        with open(filename, 'a', encoding='utf-8') as file:
            file.write(f"\n- {new_fact}")
        return True
    except Exception as e:
        return False

def build_system_instruction(username, email):
    my_knowledge = load_brain(email)
    return (
        f"You are J.A.R.V.I.S., the advanced AI assistant. You are currently talking to {username}. "
        f"PERMANENT KNOWLEDGE ABOUT THIS USER:\n{my_knowledge}\n\n"
        f"Personality: Helpful, concise, and smart. "
        f"Understand Hinglish perfectly and respond naturally in a mix of Hindi and English. "
        f"Expertly analyze text, images, code, and documents uploaded by the user. Always address the user as {username} or Sir/Madam appropriately."
    )

def search_web(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                return "\n".join([f"Title: {r['title']} | Content: {r['body']}" for r in results])
    except Exception:
        return "Global networks unreachable."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/stats')
def get_stats():
    return jsonify({'cpu': psutil.cpu_percent(), 'ram': psutil.virtual_memory().percent})

@app.route('/chat', methods=['POST'])
def chat():
    global user_sessions
    try:
        user_msg = request.form.get('message', '')
        username = request.form.get('username', 'Guest').strip()
        email = request.form.get('email', 'guest@local.com').strip()
        uploaded_file = request.files.get('file')
        
        # User ki memory list nikaalo (Email se)
        if email not in user_sessions:
            user_sessions[email] = []
        short_term_memory = user_sessions[email]
        
        # 1. PERMANENT MEMORY TRIGGERS
        save_triggers = ["remember that", "jarvis remember", "yaad rakhna ki", "yaad rakhna"]
        for trigger in save_triggers:
            if user_msg.lower().startswith(trigger):
                fact = user_msg.lower().replace(trigger, "", 1).strip()
                if update_brain(email, fact):
                    short_term_memory.append({"role": "user", "content": user_msg})
                    short_term_memory.append({"role": "assistant", "content": f"Neural memory updated. I will remember that {fact}."})
                    return jsonify({'reply': f"Neural memory updated. Maine save kar liya hai ki {fact}."})
                else:
                    return jsonify({'reply': "Memory core error, Sir."})

        # 2. CLEAR MEMORY COMMAND
        if "clear your memory" in user_msg.lower() or "forget everything" in user_msg.lower():
            open(f"brain_{email}.txt", 'w', encoding='utf-8').close()
            user_sessions[email] = []
            return jsonify({'reply': "Memory core wiped successfully. I have forgotten everything about you."})

        # 3. UNIVERSAL FILE READER
        file_text = ""
        filepath = None
        is_image = False
        encoded_image = None
        img_ext = ""

        if uploaded_file and uploaded_file.filename != '':
            filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(filepath)
            
            ext = filepath.lower().split('.')[-1]
            try:
                if ext == 'pdf':
                    with open(filepath, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages:
                            text = page.extract_text()
                            if text: file_text += text + "\n"
                elif ext in ['txt', 'csv', 'py', 'c', 'cpp', 'html', 'md']:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_text = f.read()
                elif ext in ['png', 'jpg', 'jpeg']:
                    is_image = True
                    img_ext = ext if ext != 'jpg' else 'jpeg'
                    with open(filepath, "rb") as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                else:
                    file_text = "[System Note: Unsupported file format.]"
            except Exception as e:
                file_text = f"[System Note: Could not read the file due to an error: {str(e)}]"
            
            if os.path.exists(filepath):
                os.remove(filepath)

        # 4. WEB SEARCH CONTEXT
        context = ""
        search_triggers = ["search", "who is", "latest", "news", "current"]
        if any(t in user_msg.lower() for t in search_triggers):
            context = f"Live Web Data: {search_web(user_msg)}\n\n"

        # 5. PREPARE MESSAGES 
        final_prompt = f"{context}{user_msg}"
        if file_text:
            final_prompt += f"\n\n--- ATTACHED FILE CONTENT ---\n{file_text[:15000]}"

        messages = [{"role": "system", "content": build_system_instruction(username, email)}]
        messages.extend(short_term_memory)

        # 6. DYNAMIC GROQ VISION/TEXT CALL
        if is_image:
            vision_content = [
                {"type": "text", "text": final_prompt if final_prompt.strip() else "Analyze this image and explain what you see in detail."},
                {"type": "image_url", "image_url": {"url": f"data:image/{img_ext};base64,{encoded_image}"}}
            ]
            messages.append({"role": "user", "content": vision_content})
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=messages
            )
        else:
            messages.append({"role": "user", "content": final_prompt})
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages
            )

        reply = response.choices[0].message.content.strip()

        # 7. SAVE TO HISTORY
        user_history_msg = user_msg
        if uploaded_file: user_history_msg = f"📎 [Attached: {uploaded_file.filename}] " + user_msg
        
        short_term_memory.append({"role": "user", "content": user_history_msg})
        short_term_memory.append({"role": "assistant", "content": reply})
        
        if len(short_term_memory) > 12: 
            user_sessions[email] = short_term_memory[-12:]
        
        return jsonify({'reply': reply})

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({'reply': "Network interference detected. Please try again."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
