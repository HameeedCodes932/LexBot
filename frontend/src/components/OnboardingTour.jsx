import { useState, useEffect } from 'react'
import { X, ArrowRight, ArrowLeft, Check } from 'lucide-react'

const STEPS = [
  {
    title: 'Welcome to LexBot!',
    description: 'Your AI-powered legal document assistant. Upload contracts, ask questions, extract clauses, and compare documents — all in one place.',
  },
  {
    title: 'Upload Documents',
    description: 'Start by uploading your legal documents (PDF, DOCX, or TXT). LexBot will index them and make them searchable.',
    selector: '[data-tour="upload"]',
  },
  {
    title: 'Ask Questions',
    description: 'Chat with your documents naturally. LexBot finds relevant passages and cites sources for every answer.',
    selector: '[data-tour="chat"]',
  },
  {
    title: 'Extract & Compare',
    description: 'Use the Clause Extractor and Contract Comparison tools to analyze specific provisions across documents.',
    selector: '[data-tour="tools"]',
  },
]

export default function OnboardingTour() {
  const [step, setStep] = useState(0)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const done = localStorage.getItem('lexbot_tour_done')
    if (!done) {
      setTimeout(() => setVisible(true), 500)
    }
  }, [])

  const complete = () => {
    localStorage.setItem('lexbot_tour_done', 'true')
    setVisible(false)
  }

  if (!visible) return null

  const current = STEPS[step]

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30">
      <div className="bg-white dark:bg-navy-800 rounded-2xl shadow-2xl max-w-sm w-full mx-4 p-6 animate-slide-up">
        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-1.5">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === step ? 'bg-navy-900 dark:bg-amber-400' : 'bg-gray-300 dark:bg-navy-600'
                }`}
              />
            ))}
          </div>
          <button onClick={complete} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{current.title}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-6">{current.description}</p>

        <div className="flex items-center justify-between">
          <button
            onClick={step === 0 ? complete : () => setStep((s) => s - 1)}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
          >
            {step === 0 ? 'Skip' : <><ArrowLeft size={14} className="inline mr-1" />Back</>}
          </button>
          <button
            onClick={step === STEPS.length - 1 ? complete : () => setStep((s) => s + 1)}
            className="px-4 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors flex items-center gap-1.5"
          >
            {step === STEPS.length - 1 ? (
              <><Check size={14} /> Done</>
            ) : (
              <><span>Next</span><ArrowRight size={14} /></>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
