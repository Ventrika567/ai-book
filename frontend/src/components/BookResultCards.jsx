import BookCard from './BookCard'

export default function BookResultCards({ results }) {
  if (!results || results.length === 0) return null

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-black text-brand-deep">
        Your Textbook Rental Plan
        <span className="ml-2 text-sm font-semibold text-ink-muted">({results.length} book{results.length !== 1 ? 's' : ''})</span>
      </h2>
      {results.map((result, i) => (
        <BookCard key={result.bookname || i} result={result} index={i} />
      ))}
    </div>
  )
}
