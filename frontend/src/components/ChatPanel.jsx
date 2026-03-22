import { useState, useRef, useEffect } from 'react'
import ChatBubble from './ChatBubble'

export default function ChatPanel({ messages, onSend, isLoading }) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll on new messages
  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, open])

  // Open panel when first message arrives
  useEffect(() => {
    if (messages.length > 0) setOpen(true)
  }, [messages.length])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    onSend(text)
  }

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const unread = !open && messages.length > 0

  return (
    <div className="fixed bottom-5 right-5 z-50 w-[min(500px,calc(100vw-2.5rem))] flex flex-col">
      {/* Expanded panel */}
      {open && (
        <div className="mb-4 flex flex-col bg-white/25 backdrop-blur-2xl border border-white/40 shadow-float rounded-[2rem] overflow-hidden animate-slide-up h-[600px]">
          {/* Header */}
          <div className="bg-brand-deep/90 p-5 text-white flex items-center justify-between shadow-sm">
             <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-brand/30 flex items-center justify-center border border-white/20">
                   <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                   </svg>
                </div>
                <div>
                   <p className="font-bold text-sm tracking-tight">AI Assistant</p>
                   <p className="text-[10px] opacity-70 font-semibold uppercase tracking-wider">Online</p>
                </div>
             </div>
             <button onClick={() => setOpen(false)} className="hover:bg-white/10 p-1.5 rounded-lg transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
             </button>
          </div>

          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-5 space-y-4 scroll-smooth custom-scrollbar bg-white/10"
          >
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                 <div className="w-16 h-16 rounded-3xl bg-brand/10 text-brand flex items-center justify-center mb-4">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                 </div>
                 <p className="text-brand-deep font-bold text-lg mb-2">How can I help?</p>
                 <p className="text-ink-muted text-sm">
                   Ask about your syllabus extraction, book rental optimization, or study schedule.
                 </p>
              </div>
            ) : (
              messages.map((m, i) => <ChatBubble key={i} message={m} />)
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white/90 border border-brand/10 rounded-2xl rounded-bl-none px-4 py-2.5 shadow-sm">
                  <div className="flex gap-1.5 items-center h-4">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse-soft"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="bg-white/40 border-t border-white/20 p-4 flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={2}
              className="flex-1 resize-none bg-white border border-brand/10 rounded-xl px-4 py-3 text-sm text-brand-deep shadow-inner focus:outline-none focus:ring-2 focus:ring-brand/40 transition placeholder:text-gray-400 font-medium"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="self-center bg-brand-deep text-white w-12 h-12 rounded-xl flex items-center justify-center hover:bg-brand hover:shadow-float hover:-translate-y-0.5 transition-all duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed disabled:hover:translate-y-0 cursor-pointer shadow-md"
            >
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="self-end bg-brand-deep text-white font-bold text-sm h-14 px-6 rounded-pill shadow-float hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 cursor-pointer group"
      >
        <div className="bg-white/20 p-1.5 rounded-lg group-hover:bg-white/30 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <span>{open ? 'Minimize Chat' : 'Syllabus Assistant'}</span>
        {unread && (
          <span className="w-2 h-2 rounded-full bg-brand-light animate-pulse-soft" />
        )}
      </button>
    </div>
  )
}
