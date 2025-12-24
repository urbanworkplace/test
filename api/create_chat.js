import { v4 as uuidv4 } from 'uuid';

// Simple in-memory store when no external memory is configured
let CHATS = global.__CHATS || {};
global.__CHATS = CHATS;

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const body = req.body || {};
  const title = body.title || 'New chat';
  const chat_id = uuidv4();
  CHATS[chat_id] = { title, created: new Date().toISOString(), messages: [] };

  // Note: serverless instances are ephemeral; for persistence configure external memory storage and set MEMORY_URL.
  return res.status(200).json({ chat_id });
}
