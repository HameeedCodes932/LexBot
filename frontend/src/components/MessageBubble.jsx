import { useState, useMemo } from 'react'
import { Bot, User, ChevronDown, ChevronUp, Shield, Gauge } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SourceCard from './SourceCard'
import RiskBadge from './RiskBadge'

function ConfidenceBadge({ confidence }) {
  if (!confidence || confidence.score == null) return null

  const colors = {
    High: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800',
    Medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200 dark:border-amber-800',
    Low: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-200 dark:border-red-800',
  }

  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border transition-colors ${colors[confidence.label] || colors.Medium}`}
      >
        <Gauge size={12} />
        {confidence.score}% {confidence.label}
      </button>
      {expanded && confidence.breakdown && (
        <div className="mt-2 p-2.5 bg-gray-50 dark:bg-navy-700/50 rounded-lg text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Retrieval Relevance</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">{confidence.breakdown.retrieval_relevance}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Source Coverage</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">{confidence.breakdown.source_coverage}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Answer Coherence</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">{confidence.breakdown.answer_coherence}%</span>
          </div>
        </div>
      )}
    </div>
  )
}

function ProviderBadge({ provider }) {
  if (!provider) return null
  const labels = { groq: 'Groq', openai: 'GPT-4', anthropic: 'Claude', google: 'Gemini' }
  const colors = {
    groq: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    openai: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    anthropic: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    google: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${colors[provider] || 'bg-gray-100 text-gray-600'}`}>
      <Shield size={10} />
      {labels[provider] || provider}
    </span>
  )
}

export default function MessageBubble({
  role, content, sources, risk_flags, response_time_ms, rewritten_question,
  confidence, provider, search_metadata,
}) {
  const [showSources, setShowSources] = useState(false)
  const isHuman = role === 'human'

  const markdown = useMemo(() => content || '', [content])

  return (
    <div className={`flex gap-3 ${isHuman ? 'flex-row-reverse' : ''} animate-fade-in`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isHuman ? 'bg-navy-900 dark:bg-navy-700 text-white' : 'bg-amber-400 text-navy-900'
        }`}
      >
        {isHuman ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className={`max-w-[75%] ${isHuman ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isHuman
              ? 'bg-navy-900 dark:bg-navy-700 text-white rounded-tr-md'
              : 'bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-tl-md shadow-sm'
          }`}
        >
          <div className="text-sm leading-relaxed prose prose-sm max-w-none prose-p:my-1 dark:text-gray-200">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {markdown}
            </ReactMarkdown>
          </div>
        </div>

        {/* Metadata row */}
        {!isHuman && (
          <div className="flex items-center gap-2 mt-1.5 ml-1 flex-wrap">
            {response_time_ms != null && (
              <span className="text-xs text-gray-400">{response_time_ms}ms</span>
            )}
            <ProviderBadge provider={provider} />
            {search_metadata?.hybrid_used && (
              <span className="text-xs text-gray-400 bg-gray-100 dark:bg-navy-700 px-1.5 py-0.5 rounded">Hybrid</span>
            )}
            {search_metadata?.reranker_used && (
              <span className="text-xs text-gray-400 bg-gray-100 dark:bg-navy-700 px-1.5 py-0.5 rounded">Re-ranked</span>
            )}
          </div>
        )}

        {!isHuman && rewritten_question && (
          <p className="text-xs text-gray-400 italic mt-1 ml-1">
            Rewritten: {rewritten_question}
          </p>
        )}

        {/* Confidence badge */}
        {!isHuman && confidence && <ConfidenceBadge confidence={confidence} />}

        {/* Sources */}
        {!isHuman && sources && sources.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 transition-colors"
            >
              {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              Sources ({sources.length})
            </button>
            {showSources && (
              <div className="mt-2 space-y-2">
                {sources.map((s, i) => (
                  <SourceCard key={i} {...s} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Risk flags */}
        {!isHuman && risk_flags && risk_flags.length > 0 && (
          <div className="mt-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-amber-600 dark:text-amber-400 font-semibold text-sm">Risk Alert</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {risk_flags.map((term, i) => (
                <RiskBadge key={i} term={term} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
