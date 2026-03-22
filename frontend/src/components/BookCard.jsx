import ProviderCard from './ProviderCard'

export default function BookCard({ result, index }) {
  const { bookname, author, edition, year, isbn, date_periods, best_provider, provider_link, selection_reason } = result

  return (
    <div
      className="bg-white/78 backdrop-blur-sm shadow-card rounded-xl-card overflow-hidden animate-slide-up"
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      {/* Book header */}
      <div className="bg-gradient-to-r from-brand-deep/90 to-brand/80 px-6 py-4">
        <h3 className="font-black text-white text-lg leading-snug">{bookname}</h3>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
          {author && <span className="text-brand-pale text-sm">{author}</span>}
          {edition && <span className="text-brand-pale/70 text-sm">· {edition}</span>}
          {year && <span className="text-brand-pale/70 text-sm">· {year}</span>}
          {isbn && <span className="text-brand-pale/50 text-xs font-mono mt-0.5">ISBN {isbn}</span>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1.2fr_1fr] gap-6 p-6">
        {/* Left: dates + reasoning */}
        <div className="space-y-4">
          {date_periods && date_periods.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-brand-deep uppercase tracking-widest mb-2">
                When You'll Need It
              </h4>
              <ul className="space-y-1.5">
                {date_periods.map((dp, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-brand flex-shrink-0" />
                    <span className="text-ink">
                      {dp.description}
                      {(dp.start_date || dp.end_date) && (
                        <span className="text-ink-muted ml-1">
                          ({[dp.start_date, dp.end_date].filter(Boolean).join(' – ')})
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selection_reason && (
            <div className="bg-brand-faint/80 border border-brand/20 rounded-card p-3">
              <p className="text-xs font-bold text-brand-deep uppercase tracking-widest mb-1">
                AI Reasoning
              </p>
              <p className="text-xs text-ink-muted leading-relaxed">{selection_reason}</p>
            </div>
          )}
        </div>

        {/* Right: provider card */}
        <div>
          <h4 className="text-xs font-bold text-brand-deep uppercase tracking-widest mb-2">
            Best Option
          </h4>
          <ProviderCard
            provider={best_provider}
            link={provider_link || best_provider?.provider_link}
            reason={null}
          />
        </div>
      </div>
    </div>
  )
}
