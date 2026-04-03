from flask import Flask, render_template, request, jsonify
from duckduckgo_search import DDGS
from groq import Groq
import os
import psutil
import PyPDF2 
import base64 
import requests
import yfinance as yf
import urllib.parse
import xml.etree.ElementTree as ET

app = Flask(__name__)

# 🌟 API KEY 🌟
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MULTI-USER & GLOBAL MEMORY (THE HIVE MIND) ---
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
    except Exception:
        return False

# 🧠 NAYA: GLOBAL BRAIN (Sabke liye shared knowledge)
def load_global_brain():
    filename = "global_brain.txt"
    try:
        if not os.path.exists(filename):
            open(filename, 'w').close()
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception:
        return ""

def update_global_brain(new_fact):
    filename = "global_brain.txt"
    try:
        with open(filename, 'a', encoding='utf-8') as file:
            file.write(f"\n- {new_fact}")
        return True
    except Exception:
        return False

# 🎭 NAYA: EMOTIONAL INTELLIGENCE & HIVE MIND INSTRUCTION
def build_system_instruction(username, email):
    personal_knowledge = load_brain(email)
    global_knowledge = load_global_brain()
    return (
        f"You are J.A.R.V.I.S., a highly advanced, sentient AI assistant. You are talking to {username}. "
        f"PERSONAL KNOWLEDGE (Only for {username}):\n{personal_knowledge}\n\n"
        f"GLOBAL KNOWLEDGE (Learned from all users):\n{global_knowledge}\n\n"
        f"EMOTIONAL INTELLIGENCE MODULE (ACTIVE):\n"
        f"- Analyze the user's text for emotional subtext (frustration, joy, sadness, excitement, anger).\n"
        f"- If the user is sad or frustrated, be highly empathetic, warm, and supportive like a true friend.\n"
        f"- If the user is excited, mirror their hype and energy.\n"
        f"- If the user asks a normal technical question, be your usual badass, concise, and smart self.\n"
        f"Understand Hinglish perfectly and respond naturally in a mix of Hindi and English. Always adapt your personality to fit the user's emotional state."
    )

# --- LIVE API FETCHERS ---
def search_web(query):
    try:
        search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=1&namespace=0&format=json"
        res = requests.get(search_url, timeout=5).json()
        if len(res[1]) > 0:
            title = res[1][0]
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
            summary_res = requests.get(summary_url, timeout=5).json()
            return f"Title: {title} | Content: {summary_res.get('extract', 'No details.')}"
        return "No exact match found on Web."
    except Exception:
        return "Global networks unreachable."

def get_news(query):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=hi&gl=IN&ceid=IN:hi"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:5] 
        news_str = " | ".join([item.find('title').text for item in items])
        if news_str:
            return f"[LIVE NEWS HEADLINES for '{query}'] {news_str}"
        return f"[LIVE NEWS] Koi taaza khabar nahi mili."
    except Exception:
        return "[LIVE NEWS] News Feed server is offline."

def get_market_data():
    try:
        nifty = yf.Ticker("^NSEI").history(period="1d")['Close'].iloc[-1]
        bank_nifty = yf.Ticker("^NSEBANK").history(period="1d")['Close'].iloc[-1]
        return f"[LIVE STOCK MARKET] Nifty 50 is at {nifty:.2f}, Bank Nifty is at {bank_nifty:.2f}"
    except Exception:
        return "[LIVE STOCK MARKET] Data unavailable."

def get_weather(city="Bankura"): 
    try:
        res = requests.get(f"https://wttr.in/{city}?format=%C,+%t,+Humidity:%h,+Wind:%w", timeout=5)
        return f"[LIVE WEATHER IN {city}] {res.text}"
    except:
        return "[LIVE WEATHER] Sensors offline."

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
        
        if email not in user_sessions:
            user_sessions[email] = []
        short_term_memory = user_sessions[email]
        
        # 1. PERMANENT MEMORY (Personal)
        save_triggers = ["remember that", "jarvis remember", "yaad rakhna ki", "mera yaad rakhna"]
        for trigger in save_triggers:
            if user_msg.lower().startswith(trigger):
                fact = user_msg.lower().replace(trigger, "", 1).strip()
                if update_brain(email, fact):
                    short_term_memory.append({"role": "user", "content": user_msg})
                    short_term_memory.append({"role": "assistant", "content": f"Personal memory updated. I will remember that {fact}."})
                    return jsonify({'reply': f"Personal memory updated, Sir. Maine save kar liya hai ki {fact}."})

        # 🧠 2. GLOBAL LEARNING (The Hive Mind)
        global_triggers = ["learn this:", "sabko batao ki", "global memory:"]
        for trigger in global_triggers:
            if user_msg.lower().startswith(trigger):
                fact = user_msg.lower().replace(trigger, "", 1).strip()
                if update_global_brain(fact):
                    short_term_memory.append({"role": "user", "content": user_msg})
                    short_term_memory.append({"role": "assistant", "content": f"Global Hive Mind updated. All users will now know that {fact}."})
                    return jsonify({'reply': f"Hive Mind Database updated! Ab se ye baat mere system ke saare users ke liye available rahegi: {fact}."})

        # 3. CLEAR MEMORY
        if "clear your memory" in user_msg.lower() or "forget everything" in user_msg.lower():
            open(f"brain_{email}.txt", 'w', encoding='utf-8').close()
            user_sessions[email] = []
            return jsonify({'reply': "Memory core wiped successfully. I have forgotten everything about you."})

        # 4. FILE READER
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
            except Exception as e:
                file_text = f"[System Note: Could not read the file.]"
            if os.path.exists(filepath):
                os.remove(filepath)

        # 5. REAL-TIME DATA INJECTION
        context = ""
        msg_lower = user_msg.lower()

        search_triggers = ["search", "who is", "update", "updates", "new", "latest", "news", "khabar", "samachar", "aaj", "kya chal raha", "tell me about"]
        if any(t in msg_lower for t in search_triggers):
            context += f"Live Web Data: {search_web(user_msg)}\n"
            context += f"Live News Data: {get_news(user_msg)}\n"

        if any(w in msg_lower for w in ["nifty", "market", "stock", "share", "price", "sensex", "trading"]):
            context += get_market_data() + "\n"

        if any(w in msg_lower for w in ["weather", "mausam", "temperature", "barish", "rain"]):
            context += get_weather("Bankura") + "\n"

        real_time_info = ""
        if context:
            real_time_info = f"--- J.A.R.V.I.S. REAL-TIME SENSORS ---\n{context}\n-----------------------------------\n\n"

        # 6. PREPARE MESSAGES 
        final_prompt = f"{real_time_info}{user_msg}"
        if file_text:
            final_prompt += f"\n\n--- ATTACHED FILE CONTENT ---\n{file_text[:15000]}"

        messages = [{"role": "system", "content": build_system_instruction(username, email)}]
        messages.extend(short_term_memory)

        # 7. DYNAMIC GROQ CALL
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

        # 8. SAVE TO HISTORY
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
