import ReactMarkdown from 'react-markdown'

export default function ChatBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={[
          'max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm transition-all',
          isUser
            ? 'bg-gradient-to-br from-brand to-brand-light text-white rounded-br-none'
            : 'bg-white/90 border border-brand/10 text-brand-deep rounded-bl-none prose prose-sm prose-p:leading-relaxed prose-headings:mb-2 prose-headings:mt-4',
        ].join(' ')}
      >
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown>{message.content}</ReactMarkdown>
        )}
      </div>
    </div>
  )
}
