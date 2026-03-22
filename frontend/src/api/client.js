const BASE = '/api'

export async function extractSyllabus(file) {
  const form = new FormData()
  form.append('file', file, file.name)
  const res = await fetch(`${BASE}/extract-syllabus`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Extract failed (${res.status})`)
  return res.json()
}

export async function queryProviders(books) {
  const res = await fetch(`${BASE}/query-providers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ books }),
  })
  if (!res.ok) throw new Error(`Provider query failed (${res.status})`)
  return res.json()
}

export async function selectBestProvider(bookResults) {
  const res = await fetch(`${BASE}/select-best-provider`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_results: bookResults }),
  })
  if (!res.ok) throw new Error(`Selection failed (${res.status})`)
  return res.json()
}

export async function finalizeResults(extraction, bestSelections) {
  const res = await fetch(`${BASE}/finalize-results`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extraction, best_selections: bestSelections }),
  })
  if (!res.ok) throw new Error(`Finalize failed (${res.status})`)
  return res.json()
}

export async function startChat(analysis) {
  const res = await fetch(`${BASE}/chat/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis }),
  })
  if (!res.ok) throw new Error(`Start chat failed (${res.status})`)
  return res.json()  // → { session_id: string }
}

export async function sendChatMessage(sessionId, userMessage) {
  const res = await fetch(`${BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, user_message: userMessage }),
  })
  if (!res.ok) throw new Error(`Chat failed (${res.status})`)
  return res.json()  // → { assistant_message: string }
}

export async function chatStudyPlan(analysis, userContext, userMessage, chatHistory) {
  const res = await fetch(`${BASE}/chat-study-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      analysis,
      user_context: userContext,
      user_message: userMessage,
      chat_history: chatHistory,
    }),
  })
  if (!res.ok) throw new Error(`Chat failed (${res.status})`)
  return res.json()
}
