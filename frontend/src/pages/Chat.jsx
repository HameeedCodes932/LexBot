import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Plus, MessageSquare, Download, PanelLeft, Cpu, Filter, Mic, MicOff } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import MessageBubble from '../components/MessageBubble'
import ChatHistorySidebar from '../components/ChatHistorySidebar'
import { MessageSkeleton } from '../components/LoadingSkeleton'
import { AIDisclaimerChatNotice } from '../components/AIDisclaimer'
import { sendMessage, getProviders, getDocuments, transcribeAudio } from '../api'

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

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessions, setSessions] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [streamingText, setStreamingText] = useState('')

  // Phase 4: Multi-model + document filter
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState('')
  const [documents, setDocuments] = useState([])
  const [selectedDocs, setSelectedDocs] = useState([])
  const [showDocFilter, setShowDocFilter] = useState(false)

  // Voice recording state (Plan 2)
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

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
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

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
    setSidebarOpen(false)
    setError('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const startRecording = async () => {
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
        } catch (err) {
          toast.error('Voice transcription failed')
        }
      }

      recorder.start()
      setRecording(true)
      toast.success('Recording... Speak now')
    } catch {
      toast.error('Microphone access denied')
    }
  }

  const stopRecording = () => {
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
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors"
              title="Toggle sidebar"
            >
              <PanelLeft size={16} />
            </button>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white" data-tour="chat">Chat</h2>
          </div>
          <div className="flex items-center gap-2">
            {/* Model selector */}
            {providers.length > 1 && (
              <div className="flex items-center gap-1.5">
                <Cpu size={14} className="text-gray-400" />
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

            {/* Document filter toggle */}
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
                <span className="ml-1 text-xs font-medium">{selectedDocs.length}</span>
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 font-medium transition-colors"
            >
              <Plus size={16} />
              New Session
            </button>
          </div>
        </div>

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
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 space-y-4">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-gray-500">
              <MessageSquare size={48} className="mb-3 opacity-30" />
              <p className="text-sm">Ask a question about your legal documents</p>
              <div className="mt-4 flex gap-2 text-xs text-gray-400 dark:text-gray-500">
                <span className="px-2 py-1 rounded bg-gray-100 dark:bg-navy-800 border border-gray-200 dark:border-navy-700">⌘K Focus input</span>
                <span className="px-2 py-1 rounded bg-gray-100 dark:bg-navy-800 border border-gray-200 dark:border-navy-700">⌘N New session</span>
              </div>
            </div>
          )}
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

        {/* AI Disclaimer */}
        <div className="px-4 max-w-4xl mx-auto w-full">
          <AIDisclaimerChatNotice />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-4 py-4">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your question... (⌘K to focus)"
              disabled={loading}
              className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent disabled:opacity-50 transition-colors"
            />
            <button
              onClick={recording ? stopRecording : startRecording}
              disabled={loading}
              className={`px-3 py-2.5 rounded-lg transition-colors flex items-center gap-2 ${
                recording
                  ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                  : 'bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-navy-600'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={recording ? 'Stop recording' : 'Voice input'}
            >
              {recording ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="px-4 py-2.5 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
