let CHATS = global.__CHATS || {};
global.__CHATS = CHATS;

export default async function handler(req, res) {
  const {
    query: { id }
  } = req;
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });
  if (!CHATS[id]) return res.status(404).json({ error: 'chat not found' });
  return res.status(200).json(CHATS[id]);
}
