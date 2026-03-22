import { useState, useRef } from 'react'

export default function FileUpload({ onFileSelect, disabled }) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const inputRef = useRef(null)

  const handleFile = (file) => {
    if (!file || !file.name.endsWith('.pdf')) return
    setSelectedFile(file)
    onFileSelect(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (disabled) return
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const handleChange = (e) => {
    handleFile(e.target.files[0])
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-4">
      <label
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={[
          'block cursor-pointer transition-all duration-200',
          'border-2 border-dashed rounded-xl-card p-10 text-center',
          isDragging
            ? 'border-brand-deep scale-[1.01] bg-brand-faint/60'
            : 'border-brand/40 bg-white/30 hover:border-brand hover:bg-brand-faint/40',
          disabled ? 'opacity-60 cursor-not-allowed' : '',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleChange}
          disabled={disabled}
        />

        <div className="flex flex-col items-center gap-3">
          {/* Upload icon */}
          <div className="w-14 h-14 rounded-full bg-brand/10 flex items-center justify-center">
            <svg className="w-7 h-7 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>

          {selectedFile ? (
            <div>
              <p className="font-semibold text-brand-deep text-sm mb-1">File selected</p>
              <span className="inline-block bg-brand-pale text-brand-deep rounded-pill px-3 py-1 text-sm font-medium">
                {selectedFile.name}
              </span>
            </div>
          ) : (
            <div>
              <p className="font-semibold text-ink text-base">Drop your syllabus PDF here</p>
              <p className="text-ink-muted text-sm mt-1">or click to browse</p>
            </div>
          )}
        </div>
      </label>
    </div>
  )
}
