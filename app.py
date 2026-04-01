from flask import Flask, render_template, request, jsonify
from duckduckgo_search import DDGS
from groq import Groq
import os
import psutil
import PyPDF2 
import base64 

app = Flask(__name__)

# 🌟 APNI GROQ API KEY YAHAN DAALEIN 🌟
client = Groq(api_key="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")

USER_NAME = "Nilabhra"
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MEMORY MODULE ---
short_term_memory = [] 

def load_brain():
    try:
        if not os.path.exists('brain.txt'):
            open('brain.txt', 'w').close()
        with open('brain.txt', 'r', encoding='utf-8') as file:
            return file.read()
    except Exception:
        return ""

def update_brain(new_fact):
    try:
        with open('brain.txt', 'a', encoding='utf-8') as file:
            file.write(f"\n- {new_fact}")
        return True
    except Exception as e:
        return False

my_knowledge = load_brain()

def build_system_instruction():
    global my_knowledge
    return (
        f"You are J.A.R.V.I.S., the advanced AI assistant for {USER_NAME}. "
        f"PERMANENT KNOWLEDGE ABOUT USER:\n{my_knowledge}\n\n"
        f"Personality: Helpful, concise, and smart. "
        f"Understand Hinglish perfectly and respond naturally in a mix of Hindi and English. "
        f"Expertly analyze text, images, code, and documents uploaded by the user."
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
    global my_knowledge, short_term_memory
    try:
        user_msg = request.form.get('message', '')
        uploaded_file = request.files.get('file')
        
        # 1. PERMANENT MEMORY TRIGGERS
        save_triggers = ["remember that", "jarvis remember", "yaad rakhna ki", "yaad rakhna"]
        for trigger in save_triggers:
            if user_msg.lower().startswith(trigger):
                fact = user_msg.lower().replace(trigger, "", 1).strip()
                if update_brain(fact):
                    my_knowledge += f"\n- {fact}"
                    short_term_memory.append({"role": "user", "content": user_msg})
                    short_term_memory.append({"role": "assistant", "content": f"Neural memory updated. I will remember that {fact}."})
                    return jsonify({'reply': f"Neural memory updated, Sir. Maine save kar liya hai ki {fact}."})
                else:
                    return jsonify({'reply': "Memory core error, Sir."})

        # 2. CLEAR MEMORY COMMAND
        if "clear your memory" in user_msg.lower() or "forget everything" in user_msg.lower():
            open('brain.txt', 'w', encoding='utf-8').close()
            my_knowledge = ""
            short_term_memory.clear() 
            return jsonify({'reply': "Memory core wiped successfully, Sir. I have forgotten everything."})

        # 3. SYSTEM COMMANDS
        if "open google" in user_msg.lower():
            os.system("start https://www.google.com")
            return jsonify({'reply': "Google is now active, Sir."})

        # 4. UNIVERSAL FILE READER
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

        # 5. WEB SEARCH CONTEXT
        context = ""
        search_triggers = ["search", "who is", "latest", "news", "current"]
        if any(t in user_msg.lower() for t in search_triggers):
            context = f"Live Web Data: {search_web(user_msg)}\n\n"

        # 6. PREPARE MESSAGES 
        final_prompt = f"{context}{user_msg}"
        
        if file_text:
            final_prompt += f"\n\n--- ATTACHED FILE CONTENT ---\n{file_text[:15000]}"

        messages = [{"role": "system", "content": build_system_instruction()}]
        messages.extend(short_term_memory)

        # 7. DYNAMIC GROQ VISION/TEXT CALL
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

        # 8. SAVE CURRENT CHAT TO HISTORY
        user_history_msg = user_msg
        if uploaded_file: user_history_msg = f"📎 [Attached: {uploaded_file.filename}] " + user_msg
        
        short_term_memory.append({"role": "user", "content": user_history_msg})
        short_term_memory.append({"role": "assistant", "content": reply})
        
        if len(short_term_memory) > 12: 
            short_term_memory = short_term_memory[-12:]
        
        return jsonify({'reply': reply})

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({'reply': "Network interference detected, Sir."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
