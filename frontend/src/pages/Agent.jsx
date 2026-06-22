import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, Sparkles, Terminal, Loader2, CheckCircle, XCircle, Wrench, Plus, Mic, MicOff, Volume2, VolumeX } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { runAgentCommand, transcribeAudio, speakText } from '../api'

const EXAMPLE_COMMANDS = [
  { text: 'Summarize the nda_sample.txt document', icon: '📄' },
  { text: 'Draft an email to client@firm.com about the contract review', icon: '✉️' },
  { text: 'List files in the workspace', icon: '📁' },
  { text: 'Search the web for Pakistan NDA law 2024', icon: '🔍' },
  { text: 'Create a reminder for contract deadline on 2025-06-01', icon: '⏰' },
  { text: 'Create a file called summary.txt with key NDA points', icon: '📝' },
]

function ResultCard({ data }) {
  const isSuccess = data.success
  return (
    <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-2xl rounded-tl-md p-4 shadow-sm animate-fade-in max-w-[85%]">
      {/* Thought */}
      {data.thought && (
        <p className="text-xs text-gray-400 dark:text-gray-500 italic mb-2 flex items-center gap-1.5">
          <Sparkles size={12} className="text-amber-400 flex-shrink-0" />
          {data.thought}
        </p>
      )}

      {/* Tool badge */}
      {data.tool_used && data.tool_used !== 'none' && (
        <div className="flex items-center gap-1.5 mb-3">
          <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-navy-100 dark:bg-navy-700 text-navy-600 dark:text-navy-300">
            <Wrench size={10} />
            {data.tool_used}
          </span>
          {isSuccess ? (
            <CheckCircle size={14} className="text-emerald-500" />
          ) : (
            <XCircle size={14} className="text-red-500" />
          )}
        </div>
      )}

      {/* Result */}
      {isSuccess ? (
        <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
          {typeof data.result === 'object' ? (
            <pre className="whitespace-pre-wrap break-words text-xs bg-gray-50 dark:bg-navy-900 border border-gray-100 dark:border-navy-700 rounded-lg p-3 font-mono overflow-x-auto">
              {JSON.stringify(data.result, null, 2)}
            </pre>
          ) : (
            <p className="whitespace-pre-wrap">{data.result}</p>
          )}
        </div>
      ) : (
        <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1.5">
          <XCircle size={14} className="flex-shrink-0" />
          {data.error}
        </p>
      )}
    </div>
  )
}

/**
 * Convert a structured agent result to a readable string for TTS.
 * Avoids reading raw JSON aloud.
 */
function resultToSpeechText(data) {
  if (!data || !data.success) return ''

  const result = data.result
  if (!result) return data.thought || ''

  // If it's already a string, use it directly
  if (typeof result === 'string') return result

  // For structured results, create a human-readable summary
  if (typeof result === 'object') {
    // Web search results
    if (result.results && Array.isArray(result.results)) {
      const items = result.results.slice(0, 3)
      const summaries = items.map((r, i) => `Result ${i + 1}: ${r.title}. ${r.snippet || ''}`).join('. ')
      return `I found ${result.results.length} results for "${result.query || 'your search'}". ${summaries}`
    }
    // File listing
    if (result.files && Array.isArray(result.files)) {
      const names = result.files.slice(0, 5).map(f => f.name).join(', ')
      return `The workspace contains ${result.file_count} files: ${names}${result.file_count > 5 ? ' and more' : ''}.`
    }
    // File content
    if (result.content && result.file_path) {
      return `Here is the content of ${result.file_path}: ${result.content.slice(0, 500)}`
    }
    // Draft email
    if (result.to && result.subject) {
      return `Email drafted to ${result.to} with subject "${result.subject}". ${result.status || ''}`
    }
    // Fallback: summarize keys
    return data.thought || 'Action completed successfully.'
  }

  return String(result)
}

export default function Agent() {
  const [command, setCommand] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())

  // Voice state
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [speaking, setSpeaking] = useState(false)

  // Refs
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const currentAudioRef = useRef(null)
  const recognitionRef = useRef(null)
  const finalTranscriptRef = useRef('')
  // Fallback MediaRecorder for browsers without SpeechRecognition
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
  const hasSpeechRecognition = !!SpeechRecognitionAPI

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [history, loading, scrollToBottom])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // ── Voice Recording ──────────────────────────────────────────────────────────

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
        setCommand(finalTranscriptRef.current + interim)
      }

      recognition.onerror = () => {
        setRecording(false)
        toast.error('Speech recognition error')
      }

      recognition.onend = () => {
        setRecording(false)
        const text = finalTranscriptRef.current.trim()
        if (text) {
          setCommand(text)
          toast.success('Voice transcribed')
          runCommand(text)
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

        recorder.onstop = () => {
          stream.getTracks().forEach((t) => t.stop())
          handleRecordingComplete()
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

  const handleRecordingComplete = async () => {
    const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
    if (blob.size < 1000) return

    setTranscribing(true)
    try {
      const result = await transcribeAudio(blob)
      if (result.text) {
        setCommand(result.text)
        toast.success('Voice transcribed')
        runCommand(result.text)
      }
    } catch {
      toast.error('Voice transcription failed')
    } finally {
      setTranscribing(false)
    }
  }

  // ── TTS Playback ─────────────────────────────────────────────────────────────

  const speakResponse = async (text) => {
    if (!voiceEnabled || !text || text.length < 2) return

    try {
      // Stop any currently playing audio
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }

      const audioBlob = await speakText(text)
      const url = URL.createObjectURL(audioBlob)
      const audio = new Audio(url)
      currentAudioRef.current = audio

      audio.onplay = () => setSpeaking(true)
      audio.onended = () => {
        setSpeaking(false)
        URL.revokeObjectURL(url)
        currentAudioRef.current = null
      }
      audio.onerror = () => {
        setSpeaking(false)
        URL.revokeObjectURL(url)
        currentAudioRef.current = null
      }

      await audio.play()
    } catch {
      setSpeaking(false)
      // Silently fail — TTS is non-critical
    }
  }

  // ── Command Execution ────────────────────────────────────────────────────────

  const runCommand = async (cmd) => {
    const text = cmd || command
    if (!text.trim() || loading) return

    setHistory((prev) => [...prev, { type: 'command', text }])
    setCommand('')
    setLoading(true)

    try {
      const data = await runAgentCommand(text, '', sessionId)
      setHistory((prev) => [...prev, { type: 'result', data }])

      // Speak the response
      if (data.success) {
        const speechText = resultToSpeechText(data)
        if (speechText) speakResponse(speechText)
      }
    } catch (e) {
      setHistory((prev) => [
        ...prev,
        {
          type: 'result',
          data: {
            success: false,
            error: e.response?.data?.detail || 'Agent error. Please try again.',
          },
        },
      ])
      toast.error('Agent command failed')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      runCommand()
    }
  }

  const newSession = () => {
    // Stop any playing audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
      setSpeaking(false)
    }
    setSessionId(crypto.randomUUID())
    setHistory([])
    toast.success('New session started')
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-500 flex items-center justify-center">
              <Bot size={16} className="text-navy-900" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Agent</h2>
              <p className="text-xs text-gray-400 dark:text-gray-500">Natural language commands — emails, search, files, reminders</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Speaking indicator */}
            {speaking && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 animate-pulse">
                <Volume2 size={12} className="text-emerald-500" />
                <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Speaking...</span>
              </div>
            )}

            {/* Voice toggle */}
            <button
              onClick={() => {
                const next = !voiceEnabled
                setVoiceEnabled(next)
                if (!next && currentAudioRef.current) {
                  currentAudioRef.current.pause()
                  currentAudioRef.current = null
                  setSpeaking(false)
                }
                toast.success(next ? 'Voice output enabled' : 'Voice output disabled')
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                voiceEnabled
                  ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-700 hover:bg-amber-100 dark:hover:bg-amber-900/30'
                  : 'bg-gray-100 dark:bg-navy-700 text-gray-400 dark:text-gray-500 border border-gray-200 dark:border-navy-600 hover:bg-gray-200 dark:hover:bg-navy-600'
              }`}
              title={voiceEnabled ? 'Disable voice output' : 'Enable voice output'}
            >
              {voiceEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
              {voiceEnabled ? 'Voice On' : 'Voice Off'}
            </button>

            <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
              <Terminal size={12} />
              <span>8 tools available</span>
            </div>
            <button
              onClick={newSession}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 font-medium transition-colors"
            >
              <Plus size={16} />
              New Session
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 space-y-4">
          {/* Example commands (shown when empty) */}
          {history.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-500 flex items-center justify-center mb-4 shadow-lg shadow-amber-400/20">
                <Bot size={28} className="text-navy-900" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">LexBot Agent</h3>
              <p className="text-sm text-gray-400 dark:text-gray-500 mb-2 text-center max-w-md">
                Tell me what to do in plain English. I can search the web, draft emails, manage files, set reminders, and summarize your documents.
              </p>
              <p className="text-xs text-amber-500 dark:text-amber-400 mb-6 flex items-center gap-1.5">
                <Mic size={12} />
                Click the microphone to speak your command
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-xl w-full">
                {EXAMPLE_COMMANDS.map((cmd, i) => (
                  <button
                    key={i}
                    onClick={() => runCommand(cmd.text)}
                    className="flex items-center gap-2.5 text-left px-4 py-3 rounded-xl border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 hover:border-amber-400 dark:hover:border-amber-400 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-all duration-200 hover:shadow-sm group"
                  >
                    <span className="text-base flex-shrink-0">{cmd.icon}</span>
                    <span className="truncate">{cmd.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* History */}
          {history.map((item, i) => (
            <div key={i}>
              {item.type === 'command' && (
                <div className="flex justify-end mb-1">
                  <div className="bg-navy-900 dark:bg-amber-400 text-white dark:text-navy-900 px-4 py-2.5 rounded-2xl rounded-br-md text-sm font-medium max-w-[70%] shadow-sm">
                    {item.text}
                  </div>
                </div>
              )}
              {item.type === 'result' && (
                <div className="flex gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-amber-400 flex items-center justify-center text-navy-900 flex-shrink-0 mt-0.5">
                    <Bot size={14} />
                  </div>
                  <ResultCard data={item.data} />
                </div>
              )}
            </div>
          ))}

          {/* Loading */}
          {loading && (
            <div className="flex gap-2.5">
              <div className="w-7 h-7 rounded-full bg-amber-400 flex items-center justify-center text-navy-900 flex-shrink-0">
                <Bot size={14} />
              </div>
              <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
                  <Loader2 size={14} className="animate-spin" />
                  Agent is working...
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-4 py-4">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <textarea
              ref={inputRef}
              value={command}
              onChange={(e) => {
                setCommand(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = e.target.scrollHeight + 'px'
              }}
              onKeyDown={handleKeyDown}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = e.target.scrollHeight + 'px'
              }}
              placeholder={transcribing ? 'Transcribing your voice...' : 'Tell the agent what to do...'}
              disabled={loading || transcribing}
              rows={1}
              className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent disabled:opacity-50 transition-colors resize-none overflow-y-auto max-h-32"
            />
            {/* Microphone button */}
            <button
              onClick={recording ? stopRecording : startRecording}
              disabled={loading || transcribing}
              className={`px-3 py-2.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                recording
                  ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                  : transcribing
                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-500 cursor-wait'
                    : 'bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-navy-600'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={recording ? 'Stop recording' : transcribing ? 'Transcribing...' : 'Voice input'}
            >
              {transcribing ? (
                <Loader2 size={16} className="animate-spin" />
              ) : recording ? (
                <MicOff size={16} />
              ) : (
                <Mic size={16} />
              )}
            </button>
            {/* Send button */}
            <button
              onClick={() => runCommand()}
              disabled={!command.trim() || loading}
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
