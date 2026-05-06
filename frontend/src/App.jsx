import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const USER_EMAILS = new Set(['devansh.demo@gmail.com', 'devansh.work@outlook.com'])

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
    <section className="mailbox-switcher" aria-label="Mailboxes">
      <div className="section-kicker">Mailboxes</div>
      <div className="mailbox-options">
        {mailboxes.map((mailbox) => (
          <button
            className={`mailbox-option ${
              selectedMailboxId === mailbox.mailboxId ? 'active' : ''
            }`}
            disabled={loading}
            key={mailbox.mailboxId}
            onClick={() => onChange(mailbox.mailboxId)}
            type="button"
          >
            <span>{mailbox.displayName || mailbox.email}</span>
            <small>{mailbox.email}</small>
          </button>
        ))}
      </div>
    </section>
  )
}

function getThreadMessageCount(thread, selectedThreadId, selectedThread) {
  if (
    selectedThread?.threadId === thread.threadId &&
    Array.isArray(selectedThread.messages)
  ) {
    return selectedThread.messages.length
  }

  if (selectedThreadId === thread.threadId) {
    return null
  }

  return Number.isFinite(thread.messageCount) && thread.messageCount > 0
    ? thread.messageCount
    : null
}

function ThreadList({ threads, selectedThreadId, selectedThread, onSelect, loading }) {
  return (
    <section className="thread-list-panel">
      <div className="panel-header">
        <h2>Threads</h2>
        <span className="muted">{loading ? 'Loading' : `${threads.length} total`}</span>
      </div>

      <div className="thread-list">
        {threads.map((thread) => {
          const messageCount = getThreadMessageCount(
            thread,
            selectedThreadId,
            selectedThread,
          )

          return (
            <button
              className={`thread-row ${
                selectedThreadId === thread.threadId ? 'selected' : ''
              }`}
              key={thread.threadId}
              type="button"
              onClick={() => onSelect(thread.threadId)}
            >
              <span className="thread-row-top">
                <span className="thread-subject">{thread.subject}</span>
                <span className="provider-badge">{thread.provider}</span>
              </span>
              <span className="thread-meta">
                {thread.participants?.slice(0, 2).join(', ')}
              </span>
              <span className="thread-preview">{thread.preview}</span>
              <span className="thread-foot">
                <span>
                  {messageCount ? `${messageCount} messages` : 'Messages'}
                </span>
                <span>{selectedThreadId === thread.threadId ? 'Selected' : 'Open thread'}</span>
              </span>
            </button>
          )
        })}

        {!loading && threads.length === 0 && (
          <div className="empty-state">No threads found for this mailbox.</div>
        )}
      </div>
    </section>
  )
}

function MessageCard({ message }) {
  const isMine = USER_EMAILS.has((message.from || '').toLowerCase())

  return (
    <article className={`message-card ${isMine ? 'sent' : 'received'}`}>
      <div className="message-header">
        <div>
          <strong>{isMine ? 'You' : message.from}</strong>
          {isMine && <div className="muted">{message.from}</div>}
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
        <div className="empty-state tall">
          <strong>No thread selected</strong>
          <span>Select an email thread from the left panel to inspect messages.</span>
        </div>
      )}

      {!loading && thread && (
        <>
          <div className="detail-header">
            <div className="detail-title">
              <div>
                <span className="provider-badge large">{thread.provider}</span>
                <h2>{thread.subject}</h2>
              </div>
              <span className="pill">{thread.messages?.length || 0} messages</span>
            </div>

            <div className="participants">
              {thread.participants?.map((participant) => (
                <span key={participant}>{participant}</span>
              ))}
            </div>
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
    <section className="tool-section">
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

      {!result && !error && (
        <div className="empty-state compact">
          Search across the selected mailbox to get an answer with cited sources.
        </div>
      )}

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
                <span className="source-thread-id">Thread {source.threadId}</span>
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
  if (!output) {
    return (
      <div className="empty-state compact">
        Choose Summary, Draft Reply, or Action Items to generate thread assistance.
      </div>
    )
  }

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
        <div className="action-table">
          {output.actionItems.map((item) => (
            <div className="action-item" key={`${item.sourceMessageId}-${item.task}`}>
              <span className="checkmark" aria-hidden="true"></span>
              <div>
                <strong>{item.task}</strong>
                <div className="item-meta">
                  <span>{item.owner}</span>
                  <span>Due: {item.dueDate}</span>
                  <span>{item.priority}</span>
                  <span>{item.status}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
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
    <section className="tool-section">
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
      {selectedThreadId && <SummaryOutput output={output} />}
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
        <div className="brand-lockup">
          <div className="brand-mark">M</div>
          <div>
            <h1>Mail Manager</h1>
            <p>AI-powered email search, summaries, replies, and action items</p>
          </div>
        </div>
        <div className="status-badge">AWS Connected</div>
      </header>

      {error && <div className="error global-error">{error}</div>}

      <div className="workspace">
        <aside className="panel mailbox-column">
          <MailboxSelector
            mailboxes={mailboxes}
            selectedMailboxId={selectedMailboxId}
            onChange={handleSelectMailbox}
            loading={loading.mailboxes}
          />
          <ThreadList
            threads={threads}
            selectedThreadId={selectedThreadId}
            selectedThread={selectedThread}
            onSelect={setSelectedThreadId}
            loading={loading.threads}
          />
        </aside>

        <ThreadDetail thread={selectedThread} loading={loading.thread} />

        <aside className="panel assist-column">
          <SearchPanel mailboxId={selectedMailboxId} onOpenThread={handleOpenThread} />
          <AiActionsPanel key={selectedThreadId || 'empty'} selectedThreadId={selectedThreadId} />
        </aside>
      </div>
    </main>
  )
}

export default App
