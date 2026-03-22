import { useState, useEffect } from 'react'
import { usePipeline } from './hooks/usePipeline'
import { startChat, sendChatMessage } from './api/client'

import Header from './components/Header'
import FileUpload from './components/FileUpload'
import PipelineProgress from './components/PipelineProgress'
import BookResultCards from './components/BookResultCards'
import ScheduleTimeline from './components/ScheduleTimeline'
import ChatPanel from './components/ChatPanel'

const INITIAL_STEPS = [
  { label: 'Extracting syllabus', description: 'Reading your PDF and identifying textbooks', status: 'idle', message: '' },
  { label: 'Querying providers', description: 'Searching 10 book providers for matches', status: 'idle', message: '' },
  { label: 'Selecting best deals', description: 'AI picking the lowest-cost option per book', status: 'idle', message: '' },
  { label: 'Finalizing results', description: 'Assembling your personalized rental plan', status: 'idle', message: '' },
]

export default function App() {
  const [pdfFile, setPdfFile] = useState(null)
  const [extraction, setExtraction] = useState(null)
  const [_providerResults, setProviderResults] = useState(null)
  const [_bestSelections, setBestSelections] = useState(null)
  const [finalResults, setFinalResults] = useState(null)
  const [steps, setSteps] = useState(INITIAL_STEPS)
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [pipelineStarted, setPipelineStarted] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [chatLoading, setChatLoading] = useState(false)

  const { runPipeline } = usePipeline({
    setSteps,
    setExtraction,
    setProviderResults,
    setBestSelections,
    setFinalResults,
    setPipelineRunning,
  })

  // Start a server-side chat session once the pipeline is done and results are ready
  useEffect(() => {
    if (!finalResults || !extraction) return
    startChat({ books: extraction.books, schedule_items: extraction.schedule_items })
      .then((data) => setSessionId(data.session_id))
      .catch(console.error)
  }, [finalResults])

  const handleAnalyze = () => {
    if (!pdfFile || pipelineRunning) return
    setSteps(INITIAL_STEPS)
    setExtraction(null)
    setProviderResults(null)
    setBestSelections(null)
    setFinalResults(null)
    setSessionId(null)
    setChatMessages([])
    setPipelineStarted(true)
    runPipeline(pdfFile)
  }

  const handleChatSend = async (message) => {
    if (!sessionId || chatLoading) return
    setChatMessages((prev) => [...prev, { role: 'user', content: message }])
    setChatLoading(true)
    try {
      const data = await sendChatMessage(sessionId, message)
      setChatMessages((prev) => [...prev, { role: 'assistant', content: data.assistant_message }])
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Something went wrong: ${err.message}` },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto pb-32">
        <Header />

        <FileUpload onFileSelect={setPdfFile} disabled={pipelineRunning} />

        {pdfFile && !pipelineStarted && (
          <div className="flex justify-center mt-6 animate-fade-in">
            <button
              onClick={handleAnalyze}
              className="bg-gradient-to-r from-brand-deep to-brand text-white font-bold text-base px-8 py-3.5 rounded-pill shadow-card hover:shadow-float hover:-translate-y-0.5 transition-all duration-200 cursor-pointer"
            >
              Analyze Syllabus
            </button>
          </div>
        )}

        {pipelineStarted && (
          <div className="px-4 mt-8">
            <PipelineProgress steps={steps} />
          </div>
        )}

        {finalResults && finalResults.length > 0 && (
          <div className="px-4 mt-10 space-y-8">
            {extraction?.schedule_items?.length > 0 && (
              <ScheduleTimeline scheduleItems={extraction.schedule_items} />
            )}
            <BookResultCards results={finalResults} />
          </div>
        )}
      </main>

      {sessionId && (
        <ChatPanel
          messages={chatMessages}
          onSend={handleChatSend}
          isLoading={chatLoading}
        />
      )}
    </div>
  )
}
