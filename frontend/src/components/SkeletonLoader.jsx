export default function SkeletonLoader({ lines = 3, className = '' }) {
  return (
    <div className={`space-y-2 animate-pulse-soft ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3 bg-brand-pale/80 rounded-full"
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  )
}
