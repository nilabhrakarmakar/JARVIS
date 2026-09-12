const $ = (id) => document.getElementById(id);
const state = { user: JSON.parse(localStorage.getItem('jarvisUser') || 'null'), file: null, busy: false };

function setupUser(){
  if(!state.user){
    const name = prompt('J.A.R.V.I.S. — Enter your name:', 'Guest') || 'Guest';
    const email = prompt('Enter an email/unique ID for personal memory:', 'guest@local.com') || 'guest@local.com';
    state.user = {name: name.trim().slice(0,80), email: email.trim().slice(0,180)};
    localStorage.setItem('jarvisUser', JSON.stringify(state.user));
  }
  $('sessionName').textContent = state.user.name;
  $('greeting').textContent = `Good evening, ${state.user.name}.`;
}

function addMessage(role, text){
  $('hero').style.display = 'none';
  const row = document.createElement('div'); row.className = `message ${role}`;
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
  row.appendChild(bubble); $('chatbox').appendChild(row);
  $('content').scrollTop = $('content').scrollHeight;
}

function addTyping(){
  const row = document.createElement('div'); row.className='message assistant'; row.id='typing';
  const bubble=document.createElement('div'); bubble.className='bubble typing'; bubble.textContent='J.A.R.V.I.S. is thinking…'; row.appendChild(bubble); $('chatbox').appendChild(row);
}

function removeTyping(){ $('typing')?.remove(); }

async function sendMessage(text){
  if(state.busy) return;
  const message = (text ?? $('message').value).trim();
  if(!message && !state.file) return;
  state.busy=true; $('send').disabled=true; addMessage('user', message || '[Attached file]'); addTyping();
  const form = new FormData(); form.append('message', message); form.append('username', state.user.name); form.append('email', state.user.email);
  if(state.file) form.append('file', state.file);
  try{
    const res = await fetch('/chat',{method:'POST',body:form});
    const data = await res.json(); removeTyping();
    if(!res.ok) throw new Error(data.error || 'Request failed');
    addMessage('assistant', data.reply || 'No response received.');
    addHistory(message || 'Attached file');
  }catch(err){ removeTyping(); addMessage('assistant', `System error: ${err.message}`); }
  finally{ state.busy=false; $('send').disabled=false; $('message').value=''; clearAttachment(); }
}

function addHistory(text){
  const item=document.createElement('div'); item.className='history-item'; item.textContent=text; $('history').prepend(item);
  while($('history').children.length>20) $('history').lastChild.remove();
}
function clearAttachment(){ state.file=null; $('file').value=''; $('attachment').textContent=''; }
function updateStats(){ fetch('/stats').then(r=>r.json()).then(d=>{ $('cpu').textContent=`${Math.round(d.cpu)}%`; $('ram').textContent=`${Math.round(d.ram)}%`; }).catch(()=>{}); }

$('composer').addEventListener('submit',e=>{e.preventDefault();sendMessage();});
$('attach').addEventListener('click',()=> $('file').click());
$('file').addEventListener('change',e=>{ state.file=e.target.files[0]||null; $('attachment').textContent=state.file?`📎 ${state.file.name} (${Math.ceil(state.file.size/1024)} KB)`:''; });
$('newChat').addEventListener('click',()=>{ $('chatbox').innerHTML=''; $('hero').style.display='block'; $('message').focus(); });
$('clearMemory').addEventListener('click',()=>sendMessage('forget everything'));
$('themeToggle').addEventListener('click',()=>document.body.classList.toggle('light'));
$('menuBtn').addEventListener('click',()=> $('sidebar').classList.toggle('open'));
document.querySelectorAll('[data-prompt]').forEach(b=>b.addEventListener('click',()=>{ $('message').value=b.dataset.prompt; $('message').focus(); }));
setupUser(); updateStats(); setInterval(updateStats,10000);
