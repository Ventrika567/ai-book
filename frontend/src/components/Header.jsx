export default function Header() {
  return (
    <header className="text-center py-12 px-4">
      {/* Brand row: book icon + name */}
      <div className="inline-flex items-center justify-center gap-4 mb-5">
        {/* Book icon (mirrors .brand-book from Streamlit) */}
        <div
          className="relative flex-shrink-0 rounded-[18px] shadow-card"
          style={{
            width: 66,
            height: 66,
            background: 'linear-gradient(145deg, #8f63d9 0%, #b891f5 100%)',
            boxShadow: '0 18px 32px rgba(106,70,168,0.22)',
          }}
        >
          {/* Spine */}
          <div
            className="absolute rounded-lg"
            style={{
              top: 8, bottom: 8, left: 13, width: 8,
              background: 'rgba(61,31,110,0.32)',
            }}
          />
          {/* Page */}
          <div
            className="absolute"
            style={{
              top: 12, left: 25, width: 26, height: 42,
              borderRadius: '4px 10px 10px 4px',
              background: 'rgba(255,255,255,0.9)',
            }}
          />
        </div>

        <span
          className="font-black text-brand-deep tracking-wide"
          style={{ fontSize: 'clamp(2rem, 5vw, 3.4rem)', lineHeight: 1 }}
        >
          SmartRent
        </span>
      </div>

      {/* Subtitle */}
      <p className="text-xs font-black tracking-[0.18em] uppercase text-ink-muted mb-3">
        Rent Smart — Pay Less
      </p>

      {/* Main title */}
      <h1
        className="font-black leading-tight mb-4"
        style={{ fontSize: 'min(5rem, 9vw)' }}
      >
        <span className="bg-gradient-to-r from-brand-deep to-brand bg-clip-text text-transparent">
          Your Optimized Textbook
        </span>
        <br />
        <span className="bg-gradient-to-r from-brand to-brand-light bg-clip-text text-transparent">
          Rental Engine
        </span>
      </h1>

      {/* Description */}
      <p className="text-ink-muted text-lg max-w-xl mx-auto leading-relaxed">
        Upload your syllabus and let our AI calculate your active reading dates
        to find the cheapest micro-rental.{' '}
        <strong className="text-ink">You only pay</strong> for the time you need!
      </p>
    </header>
  )
}
