export default function StudentProfile({ profile, onChange }) {
  const field = (label, key, type = 'text', placeholder = '') => (
    <div>
      <label className="block text-xs font-semibold text-brand-deep uppercase tracking-wide mb-1">
        {label}
      </label>
      <input
        type={type}
        value={profile[key]}
        onChange={(e) => onChange(key, e.target.value)}
        placeholder={placeholder}
        className="w-full bg-white/80 border border-brand/20 rounded-card px-3 py-2 text-sm text-ink placeholder-ink-muted/60 focus:outline-none focus:ring-2 focus:ring-brand/40 focus:border-brand/40 transition"
      />
    </div>
  )

  const select = (label, key, options) => (
    <div>
      <label className="block text-xs font-semibold text-brand-deep uppercase tracking-wide mb-1">
        {label}
      </label>
      <select
        value={profile[key]}
        onChange={(e) => onChange(key, e.target.value)}
        className="w-full bg-white/80 border border-brand/20 rounded-card px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/40 focus:border-brand/40 transition"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  )

  return (
    <div className="w-full max-w-2xl mx-auto px-4 mt-5">
      <div className="bg-white/20 backdrop-blur-sm border-2 border-brand/30 rounded-xl-card shadow-card p-6 animate-fade-in">
        <h2 className="font-bold text-brand-deep text-sm uppercase tracking-widest mb-4">
          Student Profile <span className="text-ink-muted font-normal normal-case tracking-normal">(optional)</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {field('Topics You Already Know', 'known_topics', 'text', 'e.g. calculus, linear algebra')}
          {field('Budget', 'budget', 'text', 'e.g. $50 total')}
          {select('Preferred Format', 'textbook_format_preference', [
            'No preference', 'Digital only', 'Print only', 'Either',
          ])}
          {select('Exam Date Flexibility', 'exam_date_flexibility', [
            'Not sure yet', 'Fixed', 'Flexible', 'Tentative',
          ])}
        </div>
      </div>
    </div>
  )
}
