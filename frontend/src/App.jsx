import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

function formatDate(value) {
  if (!value) return ''

  try {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(value))
  } catch {
    return value
  }
}

function getErrorMessage(error) {
  return error instanceof Error ? error.message : 'Something went wrong'
}

async function apiFetch(path, options = {}) {
  if (!API_BASE_URL) {
    throw new Error('Missing VITE_API_BASE_URL')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.error || `Request failed with ${response.status}`)
  }

  return data
}

function MailboxSelector({ mailboxes, selectedMailboxId, onChange, loading }) {
  return (
    <label className="field">
      <span>Mailbox</span>
      <select
        value={selectedMailboxId}
        onChange={(event) => onChange(event.target.value)}
        disabled={loading || mailboxes.length === 0}
      >
        {mailboxes.map((mailbox) => (
          <option key={mailbox.mailboxId} value={mailbox.mailboxId}>
            {mailbox.displayName || mailbox.email}
          </option>
        ))}
      </select>
    </label>
  )
}

function ThreadList({ threads, selectedThreadId, onSelect, loading }) {
  return (
    <section className="panel thread-list-panel">
      <div className="panel-header">
        <h2>Threads</h2>
        <span className="muted">{loading ? 'Loading' : `${threads.length} total`}</span>
      </div>

      <div className="thread-list">
        {threads.map((thread) => (
          <button
            className={`thread-row ${
              selectedThreadId === thread.threadId ? 'selected' : ''
            }`}
            key={thread.threadId}
            type="button"
            onClick={() => onSelect(thread.threadId)}
          >
            <span className="thread-subject">{thread.subject}</span>
            <span className="thread-meta">
              {thread.participants?.slice(0, 2).join(', ')}
            </span>
            <span className="thread-preview">{thread.preview}</span>
          </button>
        ))}

        {!loading && threads.length === 0 && (
          <div className="empty-state">No threads found for this mailbox.</div>
        )}
      </div>
    </section>
  )
}

function MessageCard({ message }) {
  return (
    <article className="message-card">
      <div className="message-header">
        <div>
          <strong>{message.from}</strong>
          <div className="muted">To {message.to?.join(', ') || 'Unknown'}</div>
        </div>
        <time>{formatDate(message.sentAt)}</time>
      </div>
      <p>{message.body}</p>
    </article>
  )
}

function ThreadDetail({ thread, loading }) {
  return (
    <section className="panel detail-panel">
      {loading && <div className="empty-state">Loading thread...</div>}

      {!loading && !thread && (
        <div className="empty-state">Select a thread to view messages.</div>
      )}

      {!loading && thread && (
        <>
          <div className="detail-title">
            <div>
              <span className="eyebrow">{thread.provider}</span>
              <h2>{thread.subject}</h2>
            </div>
            <span className="pill">{thread.messages?.length || 0} messages</span>
          </div>

          <div className="participants">
            {thread.participants?.map((participant) => (
              <span key={participant}>{participant}</span>
            ))}
          </div>

          <div className="messages">
            {thread.messages?.map((message) => (
              <MessageCard key={message.messageId} message={message} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}

function SearchPanel({ mailboxId, onOpenThread }) {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery) return

    setLoading(true)
    setError('')

    try {
      const data = await apiFetch('/search', {
        method: 'POST',
        body: JSON.stringify({ query: trimmedQuery, mailboxId }),
      })
      setResult(data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Search</h2>
        {result?.retrievalMode && <span className="muted">{result.retrievalMode}</span>}
      </div>

      <form className="search-form" onSubmit={handleSubmit}>
        <input
          aria-label="Search inbox"
          placeholder="Search approvals, deadlines, clients..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Searching' : 'Search'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="result-card search-result">
          <div className="card-title">
            <h3>Answer</h3>
            <span>{result.sources?.length || 0} sources</span>
          </div>
          <p className="answer-text">{result.answer}</p>

          <div className="card-title">
            <h3>Sources</h3>
            <span>Click to open thread</span>
          </div>
          <div className="sources">
            {result.sources?.map((source, index) => (
              <button
                className="source-card"
                key={source.messageId}
                type="button"
                onClick={() => onOpenThread(source.threadId)}
              >
                <div className="source-topline">
                  <strong>Source {index + 1}</strong>
                  <span>Score {source.score}</span>
                </div>
                <strong>{source.subject}</strong>
                <span>
                  {source.sender} · {formatDate(source.sentAt)}
                </span>
                <p>{source.snippet}</p>
              </button>
            ))}
            {result.sources?.length === 0 && (
              <div className="empty-state compact">No matching sources.</div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

function SummaryOutput({ output }) {
  if (!output) return null

  if (output.summary) {
    return (
      <div className="output-card">
        <div className="card-title">
          <h3>Summary</h3>
          <span>Template</span>
        </div>
        <p>{output.summary.short}</p>
        {output.summary.nextStep && (
          <div className="next-step">
            <span>Next Step</span>
            <strong>{output.summary.nextStep}</strong>
          </div>
        )}
        <ul>
          {output.summary.keyPoints?.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
        {output.summary.openQuestions?.length > 0 && (
          <p className="muted">
            Open: {output.summary.openQuestions.join(' ')}
          </p>
        )}
      </div>
    )
  }

  if (output.draft) {
    return (
      <div className="output-card">
        <div className="card-title">
          <h3>Draft Reply</h3>
          <span>Ready to edit</span>
        </div>
        <pre>{output.draft}</pre>
      </div>
    )
  }

  if (output.actionItems) {
    return (
      <div className="output-card">
        <div className="card-title">
          <h3>Action Items</h3>
          <span>{output.actionItems.length} found</span>
        </div>
        {output.actionItems.length === 0 && <p>No action items found.</p>}
        {output.actionItems.map((item) => (
          <div className="action-item" key={`${item.sourceMessageId}-${item.task}`}>
            <strong>{item.task}</strong>
            <div className="item-meta">
              <span>{item.owner}</span>
              <span>Due: {item.dueDate}</span>
              <span>{item.priority}</span>
              <span>{item.status}</span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return null
}

function AiActionsPanel({ selectedThreadId }) {
  const [output, setOutput] = useState(null)
  const [loadingAction, setLoadingAction] = useState('')
  const [error, setError] = useState('')

  const actions = useMemo(
    () => [
      { id: 'summary', label: 'Generate Summary', path: 'summary' },
      { id: 'draft', label: 'Draft Reply', path: 'draft-reply' },
      { id: 'actions', label: 'Action Items', path: 'action-items' },
    ],
    [],
  )

  async function runAction(action) {
    if (!selectedThreadId) return

    setLoadingAction(action.id)
    setError('')

    try {
      const data = await apiFetch(`/threads/${selectedThreadId}/${action.path}`, {
        method: 'POST',
        body: action.id === 'draft' ? JSON.stringify({}) : undefined,
      })
      setOutput(data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoadingAction('')
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>AI Assist</h2>
      </div>

      <div className="action-buttons">
        {actions.map((action) => (
          <button
            key={action.id}
            type="button"
            onClick={() => runAction(action)}
            disabled={!selectedThreadId || Boolean(loadingAction)}
          >
            {loadingAction === action.id ? 'Working' : action.label}
          </button>
        ))}
      </div>

      {!selectedThreadId && (
        <div className="empty-state compact">Select a thread to use AI actions.</div>
      )}
      {error && <div className="error">{error}</div>}
      <SummaryOutput output={output} />
    </section>
  )
}

function App() {
  const [mailboxes, setMailboxes] = useState([])
  const [selectedMailboxId, setSelectedMailboxId] = useState('')
  const [threads, setThreads] = useState([])
  const [selectedThreadId, setSelectedThreadId] = useState('')
  const [selectedThread, setSelectedThread] = useState(null)
  const [loading, setLoading] = useState({
    mailboxes: true,
    threads: false,
    thread: false,
  })
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadMailboxes() {
      setLoading((current) => ({ ...current, mailboxes: true }))
      setError('')

      try {
        const data = await apiFetch('/mailboxes')
        if (ignore) return

        const loadedMailboxes = data.mailboxes || []
        setMailboxes(loadedMailboxes)
        setSelectedMailboxId(loadedMailboxes[0]?.mailboxId || '')
      } catch (err) {
        if (!ignore) setError(getErrorMessage(err))
      } finally {
        if (!ignore) {
          setLoading((current) => ({ ...current, mailboxes: false }))
        }
      }
    }

    loadMailboxes()

    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!selectedMailboxId) {
      return
    }

    let ignore = false

    async function loadThreads() {
      setLoading((current) => ({ ...current, threads: true }))
      setError('')
      setSelectedThread(null)

      try {
        const data = await apiFetch(`/threads?mailboxId=${encodeURIComponent(selectedMailboxId)}`)
        if (ignore) return

        const loadedThreads = data.threads || []
        setThreads(loadedThreads)
        setSelectedThreadId(loadedThreads[0]?.threadId || '')
      } catch (err) {
        if (!ignore) setError(getErrorMessage(err))
      } finally {
        if (!ignore) {
          setLoading((current) => ({ ...current, threads: false }))
        }
      }
    }

    loadThreads()

    return () => {
      ignore = true
    }
  }, [selectedMailboxId])

  useEffect(() => {
    if (!selectedThreadId) return

    let ignore = false

    async function loadSelectedThread() {
      await Promise.resolve()
      if (ignore) return

      setLoading((current) => ({ ...current, thread: true }))
      setError('')

      try {
        const data = await apiFetch(`/threads/${selectedThreadId}`)
        if (!ignore) setSelectedThread(data.thread || null)
      } catch (err) {
        if (!ignore) setError(getErrorMessage(err))
      } finally {
        if (!ignore) {
          setLoading((current) => ({ ...current, thread: false }))
        }
      }
    }

    loadSelectedThread()

    return () => {
      ignore = true
    }
  }, [selectedThreadId])

  function handleSelectMailbox(mailboxId) {
    setSelectedMailboxId(mailboxId)
    setSelectedThreadId('')
    setSelectedThread(null)
    setThreads([])
  }

  function handleOpenThread(threadId) {
    setSelectedThreadId(threadId)
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <span className="eyebrow">Email RAG SaaS</span>
          <h1>Inbox Intelligence Demo</h1>
          <p>Search, cite, summarize, and draft replies from realistic inbox data.</p>
        </div>
        <MailboxSelector
          mailboxes={mailboxes}
          selectedMailboxId={selectedMailboxId}
          onChange={handleSelectMailbox}
          loading={loading.mailboxes}
        />
      </header>

      {error && <div className="error global-error">{error}</div>}

      <div className="workspace">
        <ThreadList
          threads={threads}
          selectedThreadId={selectedThreadId}
          onSelect={setSelectedThreadId}
          loading={loading.threads}
        />

        <ThreadDetail thread={selectedThread} loading={loading.thread} />

        <aside className="assist-column">
          <SearchPanel mailboxId={selectedMailboxId} onOpenThread={handleOpenThread} />
          <AiActionsPanel selectedThreadId={selectedThreadId} />
        </aside>
      </div>
    </main>
  )
}

export default App
