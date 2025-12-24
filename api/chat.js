import fetch from 'node-fetch';
import { v4 as uuidv4 } from 'uuid';

let CHATS = global.__CHATS || {};
global.__CHATS = CHATS;

// Local fallback patterns
const PATTERNS = [
  { regex: /\b(hello|hi|hey|greetings?)\b/i, replies: ["Hey there! How's it going?","Hi! Great to meet you!","Hello! What's on your mind?","Hey! How can I help you today?"] },
  { regex: /\b(how are you|how are you doing|how's it going)\b/i, replies: ["I'm doing great, thanks! How about you?","Feeling good! What about yourself?","All good here! What's happening with you?"] },
  { regex: /\b(bye|goodbye|see you|farewell)\b/i, replies: ["Goodbye! It was nice talking to you!","See you later! Take care!"] }
];

function localResponse(message) {
  for (const p of PATTERNS) {
    if (p.regex.test(message)) return p.replies[Math.floor(Math.random()*p.replies.length)];
  }
  const defaults = ["That's interesting — tell me more.", "I see. Can you elaborate a bit?", "Hmm, that's something to think about.", "I understand. What else is on your mind?"];
  return defaults[Math.floor(Math.random()*defaults.length)];
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const body = req.body || {};
  const message = (body.message || '').trim();
  if (!message) return res.status(400).json({ error: 'Message cannot be empty' });

  let chat_id = body.chat_id;
  if (!chat_id) {
    chat_id = uuidv4();
    CHATS[chat_id] = { title: message.slice(0,60) || 'New chat', created: new Date().toISOString(), messages: [] };
  }
  if (!CHATS[chat_id]) CHATS[chat_id] = { title: 'New chat', created: new Date().toISOString(), messages: [] };

  // Append user message
  CHATS[chat_id].messages.push({ role: 'user', content: message });

  const GRAQ_API_KEY = process.env.GRAQ_API_KEY;
  const GRAQ_API_URL = process.env.GRAQ_API_URL || 'https://api.groq.com/openai/v1/chat/completions';

  let bot_response = null;
  if (GRAQ_API_KEY) {
    try {
      const messages = [{ role: 'system', content: `You are little baby, a helpful AI assistant.` }, ...CHATS[chat_id].messages.map(m => ({ role: m.role, content: m.content })), { role: 'user', content: message }];
      const payload = { model: process.env.GRAQ_MODEL || 'llama-3.1-8b-instant', messages, max_tokens: 300, temperature: 0.2 };
      const r = await fetch(GRAQ_API_URL, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${GRAQ_API_KEY}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        timeout: 30000
      });
      const data = await r.json();
      if (data && data.choices && data.choices[0] && data.choices[0].message) {
        bot_response = (data.choices[0].message.content || '').toString();
      } else if (data && data.output && data.output.text) {
        bot_response = data.output.text;
      } else {
        bot_response = null;
      }
    } catch (e) {
      console.error('Graq error', e);
      bot_response = null;
    }
  }

  if (!bot_response) bot_response = localResponse(message);

  CHATS[chat_id].messages.push({ role: 'assistant', content: bot_response });

  // Note: persistence is ephemeral in serverless. For persistent memory configure external storage.
  return res.status(200).json({ chat_id, response: bot_response });
}
