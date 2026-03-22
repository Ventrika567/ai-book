import {
  extractSyllabus,
  queryProviders,
  selectBestProvider,
  finalizeResults,
} from '../api/client'

export function usePipeline({
  setSteps,
  setExtraction,
  setProviderResults,
  setBestSelections,
  setFinalResults,
  setPipelineRunning,
}) {
  const runPipeline = async (file) => {
    setPipelineRunning(true)

    const upd = (i, status, message = '') =>
      setSteps((prev) => prev.map((s, j) => (j === i ? { ...s, status, message } : s)))

    try {
      upd(0, 'running')
      const extraction = await extractSyllabus(file)
      if (!extraction.books?.length) {
        upd(0, 'error', 'No textbooks detected in the syllabus.')
        return
      }
      setExtraction(extraction)
      upd(
        0,
        'done',
        `Found ${extraction.books.length} book${extraction.books.length !== 1 ? 's' : ''} and ${extraction.schedule_items?.length ?? 0} schedule items.`
      )

      upd(1, 'running')
      const providerResults = await queryProviders(extraction.books)
      setProviderResults(providerResults)
      const total = providerResults.reduce((s, r) => s + (r.providers?.length ?? 0), 0)
      upd(1, 'done', `Retrieved ${total} provider match${total !== 1 ? 'es' : ''}.`)

      upd(2, 'running')
      const bestSelections = await selectBestProvider(
        providerResults.map((r) => ({ bookname: r.bookname, providers: r.providers ?? [] }))
      )
      setBestSelections(bestSelections)
      upd(2, 'done', 'Best provider determined for each book.')

      upd(3, 'running')
      const final = await finalizeResults(extraction, bestSelections)
      setFinalResults(final)
      upd(3, 'done', 'Your optimized rental strategy is ready!')
    } catch (err) {
      setSteps((prev) =>
        prev.map((s) => (s.status === 'running' ? { ...s, status: 'error', message: err.message } : s))
      )
    } finally {
      setPipelineRunning(false)
    }
  }

  return { runPipeline }
}
