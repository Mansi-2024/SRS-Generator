import { useState, useMemo } from 'react'

// ── Vague word highlighter ────────────────────────────────────────────────
function highlightVagueWords(sentence, vagueWords) {
    if (!vagueWords || vagueWords.length === 0) return sentence
    const sorted = [...vagueWords].sort((a, b) => b.length - a.length)
    const escaped = sorted.map(w => w.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&'))
    const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
    const parts = sentence.split(regex)
    return parts.map((part, i) => {
        if (vagueWords.some(w => w.toLowerCase() === part.toLowerCase())) {
            return <mark key={i} className="vague-highlight">{part}</mark>
        }
        return part
    })
}

// ── Type badge ────────────────────────────────────────────────────────────
function TypeBadge({ type }) {
    return <span className={`req-type-badge badge-${type}`}>{type}</span>
}

// ── Single editable row ────────────────────────────────────────────────────
function ReqRow({ req, idx, onUpdate, onDelete }) {
    const [editing, setEditing] = useState(false)
    const [draft, setDraft] = useState(req.sentence)

    const commitEdit = () => {
        if (draft.trim()) onUpdate(req.id, { sentence: draft.trim() })
        setEditing(false)
    }

    const toggleType = () => {
        onUpdate(req.id, { type: req.type === 'FR' ? 'NFR' : 'FR' })
    }

    return (
        <tr className={`req-row ${req.is_vague ? 'row-vague' : ''}`} style={{ animationDelay: `${idx * 0.03}s` }}>
            {/* ID */}
            <td className="cell-id">
                <span className="req-id">#{String(req.id).padStart(3, '0')}</span>
            </td>

            {/* Requirement Text */}
            <td className="cell-text" onClick={() => !editing && setEditing(true)}>
                {editing ? (
                    <textarea
                        autoFocus
                        className="req-textarea"
                        value={draft}
                        rows={Math.max(2, Math.ceil(draft.length / 80))}
                        onChange={e => setDraft(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitEdit() } if (e.key === 'Escape') { setDraft(req.sentence); setEditing(false) } }}
                    />
                ) : (
                    <p className="req-sentence-text">
                        {highlightVagueWords(req.sentence, req.vague_words)}
                        <span className="edit-hint">✏️</span>
                    </p>
                )}
                {req.vague_words?.length > 0 && !editing && (
                    <div className="vague-words-list" style={{ marginTop: '6px' }}>
                        {req.vague_words.map((w, i) => <span key={i} className="vague-tag">{w}</span>)}
                    </div>
                )}
            </td>

            {/* Type (clickable toggle) */}
            <td className="cell-type">
                <button
                    className={`type-toggle badge-${req.type}`}
                    onClick={toggleType}
                    title="Click to toggle FR ↔ NFR"
                >
                    {req.type}
                    <span style={{ opacity: 0.5, fontSize: '0.6rem', marginLeft: 3 }}>⇄</span>
                </button>
            </td>

            {/* Vague status */}
            <td className="cell-vague">
                {req.is_vague
                    ? <span className="vague-badge">⚠️ Vague</span>
                    : <span className="clear-badge">✓ Clear</span>
                }
            </td>

            {/* Actions */}
            <td className="cell-actions">
                <button
                    className="row-action-btn btn-delete"
                    onClick={() => onDelete(req.id)}
                    title="Delete requirement"
                >✕</button>
            </td>
        </tr>
    )
}

// ── Main editor ────────────────────────────────────────────────────────────
export default function RequirementsEditor({ requirements, setRequirements, nonRequirements }) {
    const [filter, setFilter] = useState('ALL')
    const [showNonReqs, setShowNonReqs] = useState(false)

    // ── CRUD handlers ──
    const handleUpdate = (id, changes) => {
        setRequirements(prev => prev.map(r =>
            r.id === id ? { ...r, ...changes } : r
        ))
    }

    const handleDelete = (id) => {
        setRequirements(prev => prev.filter(r => r.id !== id))
    }

    const handleAdd = () => {
        const maxId = requirements.reduce((m, r) => Math.max(m, r.id), 0)
        setRequirements(prev => [...prev, {
            id: maxId + 1,
            sentence: '',
            type: 'FR',
            is_vague: false,
            vague_words: [],
        }])
        setFilter('ALL')
    }

    // ── Filtering ──
    const filtered = useMemo(() => {
        if (filter === 'ALL')   return requirements
        if (filter === 'VAGUE') return requirements.filter(r => r.is_vague)
        return requirements.filter(r => r.type === filter)
    }, [requirements, filter])

    const FILTERS = [
        { key: 'ALL',   label: 'All',           count: requirements.length },
        { key: 'FR',    label: '⚡ Functional',  count: requirements.filter(r => r.type === 'FR').length },
        { key: 'NFR',   label: '🛡️ Non-Functional', count: requirements.filter(r => r.type === 'NFR').length },
        { key: 'VAGUE', label: '⚠️ Vague',      count: requirements.filter(r => r.is_vague).length },
    ]

    return (
        <div className="editor-section">
            {/* Header */}
            <div className="editor-header">
                <div>
                    <h2 className="section-title">Requirements Editor</h2>
                    <p className="section-sub">
                        Edit, reclassify, or delete requirements. Changes will be reflected in the generated SRS.
                    </p>
                </div>
                <button className="btn btn-add-req" onClick={handleAdd} id="add-req-btn">
                    + Add Requirement
                </button>
            </div>

            {/* Filter + count bar */}
            <div className="table-controls">
                <div className="filter-btns">
                    {FILTERS.map(f => (
                        <button
                            key={f.key}
                            className={`filter-btn ${filter === f.key ? `active-${f.key}` : ''}`}
                            onClick={() => setFilter(f.key)}
                            id={`filter-${f.key.toLowerCase()}`}
                        >
                            {f.label} <span style={{ opacity: 0.55, marginLeft: 3 }}>({f.count})</span>
                        </button>
                    ))}
                </div>
                <span className="count-badge">
                    {filtered.length} / {requirements.length} shown
                </span>
            </div>

            {/* Table */}
            <div className="req-table-wrapper">
                {filtered.length === 0 ? (
                    <div className="empty-state">
                        <span className="empty-icon">🔍</span>
                        No requirements match this filter.
                    </div>
                ) : (
                    <table className="req-table" id="requirements-table">
                        <thead>
                            <tr>
                                <th className="th-id">ID</th>
                                <th className="th-text">Requirement Text <span className="th-hint">(click text to edit)</span></th>
                                <th className="th-type">Type</th>
                                <th className="th-vague">Ambiguity</th>
                                <th className="th-actions"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((req, idx) => (
                                <ReqRow
                                    key={req.id}
                                    req={req}
                                    idx={idx}
                                    onUpdate={handleUpdate}
                                    onDelete={handleDelete}
                                />
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Non-requirements collapse */}
            {nonRequirements?.length > 0 && (
                <div className="non-reqs-section">
                    <button
                        className="btn btn-outline btn-sm"
                        onClick={() => setShowNonReqs(s => !s)}
                        id="toggle-non-reqs"
                        style={{ marginBottom: '12px' }}
                    >
                        {showNonReqs ? '▲ Hide' : '▼ Show'} Non-Requirement Sentences ({nonRequirements.length})
                    </button>
                    {showNonReqs && (
                        <div className="non-req-list">
                            {nonRequirements.map(item => (
                                <div key={item.id} className="non-req-item">
                                    <span className="non-req-dot" />
                                    {item.sentence}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
