const modePill = {
  borrow: 'bg-emerald-100 text-emerald-700',
  free: 'bg-emerald-100 text-emerald-700',
  buy: 'bg-brand-faint text-brand-deep',
  rent: 'bg-amber-100 text-amber-700',
}

export default function ProviderCard({ provider, link, reason }) {
  if (!provider) {
    return (
      <div className="bg-white/60 border border-brand-pale rounded-card p-4 text-center">
        <p className="text-ink-muted text-sm">No provider found for this book.</p>
      </div>
    )
  }

  const mode = provider.acquisition_mode?.toLowerCase() || ''
  const cost = provider.estimated_cost
  const isFree = mode === 'borrow' || mode === 'free' || cost === 0 || cost === null

  const costDisplay = isFree ? (
    <span className="text-xl font-black text-emerald-600">Free</span>
  ) : cost != null ? (
    <span className="text-xl font-black text-ink">${Number(cost).toFixed(2)}</span>
  ) : (
    <span className="text-sm text-ink-muted italic">Price unknown</span>
  )

  const pillClass = modePill[mode] || 'bg-brand-faint text-brand-deep'
  const bookInfo = provider.book_info || {}

  return (
    <div className="bg-white border border-brand-pale shadow-soft rounded-card p-4 flex flex-col gap-3">
      {/* Provider header */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="font-bold text-sm text-ink truncate">{provider.provider || 'Unknown provider'}</span>
        {mode && (
          <span className={`text-xs font-semibold rounded-pill px-2.5 py-0.5 ${pillClass}`}>
            {mode.charAt(0).toUpperCase() + mode.slice(1)}
          </span>
        )}
      </div>

      {/* Cost + format grid */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-ink-muted uppercase tracking-wide font-semibold mb-0.5">Cost</p>
          {costDisplay}
        </div>
        <div>
          <p className="text-xs text-ink-muted uppercase tracking-wide font-semibold mb-0.5">Format</p>
          <p className="text-sm text-ink capitalize">{provider.price_type || bookInfo.format || '—'}</p>
        </div>
      </div>

      {/* AI reason */}
      {reason && (
        <p className="text-xs text-ink-muted italic border-t border-brand-pale/60 pt-2">
          {reason}
        </p>
      )}

      {/* CTA */}
      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-center bg-gradient-to-r from-brand to-brand-light text-white text-sm font-semibold py-2.5 rounded-card hover:shadow-float hover:-translate-y-0.5 transition-all duration-200 mt-auto"
        >
          View on {provider.provider || 'Provider'} →
        </a>
      ) : (
        <button
          disabled
          className="block w-full text-center bg-brand-pale text-brand-deep/50 text-sm font-semibold py-2.5 rounded-card cursor-not-allowed mt-auto"
        >
          No link available
        </button>
      )}
    </div>
  )
}
