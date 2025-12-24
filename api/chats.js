// Return list of chats available in-memory or via MEMORY_URL
let CHATS = global.__CHATS || {};
global.__CHATS = CHATS;

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });
  const out = Object.entries(CHATS).map(([k, v]) => ({ chat_id: k, title: v.title, created: v.created }));
  res.status(200).json(out);
}
