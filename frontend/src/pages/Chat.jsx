import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Plus, MessageSquare, Download, Cpu, Filter, Mic, MicOff, Scale } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import MessageBubble from '../components/MessageBubble'
import ChatHistorySidebar from '../components/ChatHistorySidebar'
import { AIDisclaimerChatNotice } from '../components/AIDisclaimer'
import { sendMessage, getProviders, getDocuments, transcribeAudio } from '../api'
import { useLayout } from '../context/LayoutContext'

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-amber-400 flex items-center justify-center text-navy-900 flex-shrink-0">
        <MessageSquare size={14} />
      </div>
      <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
          <span className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
          <span className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
        </div>
      </div>
    </div>
  )
}

function ChatEmptyState({ onSuggestion }) {
  const kbd =
    'px-1.5 py-0.5 rounded bg-gray-100 dark:bg-navy-800 border border-gray-200 dark:border-navy-700 text-gray-500 dark:text-gray-400 font-medium'
  const suggestions = [
    'Summarize this NDA',
    'Find termination clauses',
    'Highlight liability risks',
    'Compare two contracts',
  ]
  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-16">
      <div className="w-11 h-11 rounded-xl bg-amber-400 flex items-center justify-center mb-6">
        <Scale size={20} className="text-navy-900" />
      </div>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
        What can I help you review?
      </h2>
      <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400 text-center">
        Ask about your legal documents, clauses, obligations, or risks.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2 max-w-lg">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="px-3.5 py-1.5 rounded-lg text-[13px] font-medium text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-600 hover:text-navy-900 dark:hover:text-white transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[11px] text-gray-400 dark:text-gray-500">
        <span>
          <kbd className={kbd}>Ctrl K</kbd> Focus input
        </span>
        <span>
          <kbd className={kbd}>Ctrl N</kbd> New session
        </span>
        <span>
          <kbd className={kbd}>Ctrl B</kbd> Toggle sidebar
        </span>
      </div>
    </div>
  )
}

export default function Chat() {
  const { sessionsOpen, setSessionsOpen, toggleSidebar } = useLayout()
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessions, setSessions] = useState([])
  const [streamingText, setStreamingText] = useState('')

  // Phase 4: Multi-model + document filter
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState('')
  const [documents, setDocuments] = useState([])
  const [selectedDocs, setSelectedDocs] = useState([])
  const [showDocFilter, setShowDocFilter] = useState(false)

  // Voice recording state
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const recognitionRef = useRef(null)
  const finalTranscriptRef = useRef('')

  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
  const hasSpeechRecognition = !!SpeechRecognitionAPI

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, loading, streamingText, scrollToBottom])

  // Load providers and documents on mount
  useEffect(() => {
    getProviders()
      .then((p) => {
        setProviders(p)
        const def = p.find((x) => x.is_default)
        if (def) setSelectedProvider(def.name)
      })
      .catch(() => {})

    getDocuments(1, 100)
      .then((d) => setDocuments(d.items || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault()
        newSession()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault()
        toggleSidebar()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggleSidebar])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const q = input.trim()
    setInput('')
    setError('')

    const humanMsg = { role: 'human', content: q }
    setMessages((prev) => [...prev, humanMsg])
    setLoading(true)
    setStreamingText('')

    try {
      const data = await sendMessage(
        q,
        sessionId,
        selectedProvider || null,
        selectedDocs.length > 0 ? selectedDocs : null,
      )
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources || [],
          risk_flags: data.risk_flags || [],
          response_time_ms: data.response_time_ms,
          rewritten_question: data.rewritten_question,
          confidence: data.confidence,
          provider: data.provider,
          search_metadata: data.search_metadata,
        },
      ])
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to get response.'
      setError(detail)
      toast.error(detail)
    } finally {
      setLoading(false)
      setStreamingText('')
    }
  }

  const newSession = () => {
    setSessionId(crypto.randomUUID())
    setMessages([])
    setError('')
    toast.success('New session started')
  }

  const selectSession = (id) => {
    setSessionId(id)
    setMessages([])
    setSessionsOpen(false)
    setError('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const startRecording = async () => {
    if (hasSpeechRecognition) {
      const recognition = new SpeechRecognitionAPI()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      recognitionRef.current = recognition

      finalTranscriptRef.current = ''

      recognition.onresult = (event) => {
        let final = ''
        let interim = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          if (result.isFinal) {
            final += result[0].transcript
          } else {
            interim += result[0].transcript
          }
        }
        finalTranscriptRef.current += final
        setInput(finalTranscriptRef.current + interim)
      }

      recognition.onerror = (event) => {
        setRecording(false)
        const reasons = {
          'not-allowed': 'Microphone access was denied. Check browser permissions.',
          'no-speech': 'No speech detected. Try again.',
          'audio-capture': 'No microphone found.',
          network: 'Speech recognition is offline. Check your internet connection.',
          aborted: 'Speech recognition was cancelled.',
          'service-not-allowed': 'Speech service unavailable in this browser/region.',
        }
        toast.error(`Speech recognition error: ${reasons[event.error] || event.error}`)
      }

      recognition.onend = () => {
        setRecording(false)
        const text = finalTranscriptRef.current.trim()
        if (text) {
          setInput((prev) => (prev ? prev + ' ' + text : text))
          toast.success('Voice transcribed')
        }
        finalTranscriptRef.current = ''
      }

      recognition.start()
      setRecording(true)
    } else {
      // Fallback: MediaRecorder + server-side transcription
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        audioChunksRef.current = []
        const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
        mediaRecorderRef.current = recorder

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data)
        }

        recorder.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop())
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
          if (blob.size < 1000) return
          try {
            const result = await transcribeAudio(blob)
            if (result.text) {
              setInput((prev) => (prev ? prev + ' ' + result.text : result.text))
              toast.success('Voice transcribed')
            }
          } catch {
            toast.error('Voice transcription failed')
          }
          setRecording(false)
        }

        recorder.start()
        setRecording(true)
      } catch {
        toast.error('Microphone access denied')
      }
    }
  }

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    setRecording(false)
  }

  const toggleDocFilter = (filename) => {
    setSelectedDocs((prev) =>
      prev.includes(filename)
        ? prev.filter((d) => d !== filename)
        : [...prev, filename]
    )
  }

  const exportChat = () => {
    if (messages.length === 0) {
      toast.error('No messages to export')
      return
    }
    const text = messages
      .map((m) => `${m.role === 'human' ? 'You' : 'LexBot'}:\n${m.content}`)
      .join('\n\n---\n\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `lexbot-chat-${sessionId.slice(0, 8)}.txt`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Chat exported')
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <ChatHistorySidebar
        sessionId={sessionId}
        onSelectSession={selectSession}
        onNewSession={newSession}
        sessions={sessions}
        setSessions={setSessions}
        isOpen={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <WorkspaceTopBar
          title="Chat"
          titleProps={{ 'data-tour': 'chat' }}
          showSessionsToggle
          actions={
            <>
              {providers.length > 1 && (
                <div className="flex items-center gap-1.5 mr-1">
                  <Cpu size={13} className="text-gray-400" />
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="text-xs bg-gray-100 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-lg px-2 py-1.5 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-amber-400"
                  >
                    {providers.map((p) => (
                      <option key={p.name} value={p.name}>
                        {p.name === 'groq' ? 'Groq (Llama)' : p.name === 'openai' ? 'GPT-4o' : p.name === 'anthropic' ? 'Claude' : p.name === 'google' ? 'Gemini' : p.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                onClick={() => setShowDocFilter(!showDocFilter)}
                className={`p-2 rounded-lg transition-colors ${
                  selectedDocs.length > 0
                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                    : 'hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400'
                }`}
                title={selectedDocs.length > 0 ? `Filtering ${selectedDocs.length} doc(s)` : 'Filter by documents'}
              >
                <Filter size={16} />
                {selectedDocs.length > 0 && (
                  <span className="ml-0.5 text-xs font-medium">{selectedDocs.length}</span>
                )}
              </button>

              <button
                onClick={exportChat}
                disabled={messages.length === 0}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 disabled:opacity-30 transition-colors"
                title="Export chat"
              >
                <Download size={16} />
              </button>
              <button
                onClick={newSession}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 hover:bg-gray-100 dark:hover:bg-navy-700 font-medium transition-colors"
              >
                <Plus size={16} />
                <span className="hidden md:inline">New Session</span>
              </button>
            </>
          }
        />

        {/* Document filter panel */}
        {showDocFilter && documents.length > 0 && (
          <div className="px-4 md:px-6 py-2 border-b border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-800/50">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-500 dark:text-gray-400 mr-1">Search in:</span>
              <button
                onClick={() => setSelectedDocs([])}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  selectedDocs.length === 0
                    ? 'bg-navy-900 dark:bg-amber-400 text-white dark:text-navy-900 border-transparent'
                    : 'border-gray-300 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:border-navy-900 dark:hover:border-amber-400'
                }`}
              >
                All Documents
              </button>
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => toggleDocFilter(doc.filename)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors truncate max-w-[200px] ${
                    selectedDocs.includes(doc.filename)
                      ? 'bg-navy-900 dark:bg-amber-400 text-white dark:text-navy-900 border-transparent'
                      : 'border-gray-300 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:border-navy-900 dark:hover:border-amber-400'
                  }`}
                >
                  {doc.filename}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !loading ? (
            <ChatEmptyState
              onSuggestion={(s) => {
                setInput(s)
                inputRef.current?.focus()
              }}
            />
          ) : (
            <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-5">
              {messages.map((msg, i) => (
                <MessageBubble key={i} {...msg} />
              ))}
              {loading && (
                streamingText ? (
                  <MessageBubble role="assistant" content={streamingText} />
                ) : (
                  <TypingIndicator />
                )
              )}
              {error && !loading && (
                <div className="text-center">
                  <p className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400 inline-block px-4 py-2 rounded-lg">{error}</p>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* AI Disclaimer */}
        <div className="max-w-3xl mx-auto w-full px-4 md:px-6 pt-4">
          <AIDisclaimerChatNotice />
        </div>

        {/* Composer */}
        <div className="px-4 md:px-6 pt-3 pb-4">
          <div className="max-w-3xl mx-auto">
            <div className="rounded-xl border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 shadow-sm px-3.5 py-2.5 transition-colors focus-within:border-gray-300 dark:focus-within:border-navy-600">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value)
                  e.target.style.height = 'auto'
                  e.target.style.height = e.target.scrollHeight + 'px'
                }}
                onKeyDown={handleKeyDown}
                onInput={(e) => {
                  e.target.style.height = 'auto'
                  e.target.style.height = e.target.scrollHeight + 'px'
                }}
                placeholder={recording ? 'Listening... Speak now' : 'Ask a question about your documents'}
                disabled={loading}
                rows={1}
                className="w-full bg-transparent resize-none outline-none text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 max-h-32 overflow-y-auto disabled:opacity-50"
              />
              <div className="flex items-center justify-between mt-1.5">
                <div className="flex items-center gap-1">
                  <button
                    onClick={recording ? stopRecording : startRecording}
                    disabled={loading}
                    className={`p-1.5 rounded-lg transition-colors ${
                      recording
                        ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                        : 'text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-navy-700'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    title={recording ? 'Stop recording' : 'Voice input'}
                  >
                    {recording ? <MicOff size={16} /> : <Mic size={16} />}
                  </button>
                  {input && (
                    <span className="hidden sm:inline text-[11px] text-gray-400 dark:text-gray-500 ml-1">
                      Enter to send &middot; Shift+Enter for new line
                    </span>
                  )}
                </div>
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-400 text-navy-900 font-medium text-sm hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-navy-900 border-t-transparent" />
                      Working...
                    </>
                  ) : (
                    <>
                      <Send size={14} />
                      Send
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
