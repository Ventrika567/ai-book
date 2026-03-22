import { useState } from 'react'

const typeStyle = {
  exam:       'bg-red-100 text-red-700',
  quiz:       'bg-orange-100 text-orange-700',
  homework:   'bg-blue-100 text-blue-700',
  assignment: 'bg-blue-100 text-blue-700',
  reading:    'bg-green-100 text-green-700',
  deadline:   'bg-purple-100 text-purple-700',
}

const getStyle = (type) => typeStyle[type?.toLowerCase()] || 'bg-gray-100 text-gray-600'

export default function ScheduleTimeline({ scheduleItems }) {
  const [open, setOpen] = useState(false)

  if (!scheduleItems || scheduleItems.length === 0) return null

  return (
    <div className="bg-white/20 backdrop-blur-sm border border-brand/20 rounded-xl-card shadow-card overflow-hidden animate-fade-in">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-brand-faint/30 transition cursor-pointer"
      >
        <div>
          <h2 className="font-black text-brand-deep text-sm uppercase tracking-widest">
            Course Schedule
          </h2>
          <p className="text-xs text-ink-muted mt-0.5">{scheduleItems.length} items</p>
        </div>
        <svg
          className={`w-5 h-5 text-brand transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div
        className="overflow-hidden transition-all duration-300"
        style={{ maxHeight: open ? '9999px' : '0' }}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-t border-brand-pale/60 bg-brand-faint/40">
                <th className="text-left px-6 py-2 text-xs font-bold text-brand-deep uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-2 text-xs font-bold text-brand-deep uppercase tracking-wide">Label</th>
                <th className="text-left px-4 py-2 text-xs font-bold text-brand-deep uppercase tracking-wide">Date</th>
              </tr>
            </thead>
            <tbody>
              {scheduleItems.map((item, i) => (
                <tr key={i} className="border-t border-brand-pale/40 hover:bg-brand-faint/20 transition">
                  <td className="px-6 py-2.5">
                    <span className={`text-xs font-semibold rounded-pill px-2.5 py-0.5 ${getStyle(item.item_type)}`}>
                      {item.item_type || 'other'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-ink">{item.label}</td>
                  <td className="px-4 py-2.5 text-ink-muted">{item.date_text || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
