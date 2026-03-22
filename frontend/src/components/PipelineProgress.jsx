const StatusIcon = ({ status }) => {
  if (status === 'running') {
    return (
      <svg
        className="w-5 h-5 text-brand animate-spin-slow"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a10 10 0 100 10h-4a8 8 0 01-8-8z" />
      </svg>
    )
  }
  if (status === 'done') {
    return (
      <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
    )
  }
  if (status === 'error') {
    return (
      <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
      </svg>
    )
  }
  // idle
  return <div className="w-2.5 h-2.5 rounded-full bg-brand-pale" />
}

const ringColor = {
  idle: 'border-brand-pale/60 bg-white/40',
  running: 'border-brand bg-brand-faint shadow-[0_0_0_4px_rgba(143,99,217,0.12)]',
  done: 'border-emerald-300 bg-emerald-50',
  error: 'border-red-300 bg-red-50',
}

export default function PipelineProgress({ steps }) {
  return (
    <div className="w-full max-w-xl mx-auto bg-white/20 backdrop-blur-sm border border-brand/20 rounded-xl-card shadow-card p-6 animate-fade-in">
      <h2 className="text-xs font-bold text-brand-deep uppercase tracking-widest mb-5">
        Analysis Progress
      </h2>

      <div className="relative">
        {steps.map((step, i) => (
          <div
            key={i}
            className="flex gap-4 animate-slide-up"
            style={{ animationDelay: `${i * 0.08}s` }}
          >
            {/* Icon + connector line */}
            <div className="flex flex-col items-center">
              <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all duration-300 ${ringColor[step.status]}`}>
                <StatusIcon status={step.status} />
              </div>
              {i < steps.length - 1 && (
                <div className={`w-0.5 flex-1 my-1 transition-colors duration-500 ${step.status === 'done' ? 'bg-emerald-300' : 'bg-brand-pale'}`} />
              )}
            </div>

            {/* Label + message */}
            <div className={`pb-5 ${i === steps.length - 1 ? 'pb-0' : ''}`}>
              <p className={`font-semibold text-sm leading-tight transition-colors ${step.status === 'running' ? 'text-brand-deep' : step.status === 'done' ? 'text-emerald-700' : step.status === 'error' ? 'text-red-700' : 'text-ink-muted'}`}>
                {step.label}
              </p>
              <p className="text-xs text-ink-muted mt-0.5">
                {step.message || step.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
