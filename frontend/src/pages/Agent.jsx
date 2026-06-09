import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, Sparkles, Terminal, Loader2, CheckCircle, XCircle, Wrench, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { runAgentCommand } from '../api'

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

export default function Agent() {
  const [command, setCommand] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [history, loading, scrollToBottom])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const runCommand = async (cmd) => {
    const text = cmd || command
    if (!text.trim() || loading) return

    setHistory((prev) => [...prev, { type: 'command', text }])
    setCommand('')
    setLoading(true)

    try {
      const data = await runAgentCommand(text, '', sessionId)
      setHistory((prev) => [...prev, { type: 'result', data }])
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
              <p className="text-sm text-gray-400 dark:text-gray-500 mb-6 text-center max-w-md">
                Tell me what to do in plain English. I can search the web, draft emails, manage files, set reminders, and summarize your documents.
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
            <input
              ref={inputRef}
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Tell the agent what to do..."
              disabled={loading}
              className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent disabled:opacity-50 transition-colors"
            />
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
