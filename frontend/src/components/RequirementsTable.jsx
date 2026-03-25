import { useState, useMemo } from 'react'

function highlightVagueWords(sentence, vagueWords) {
    if (!vagueWords || vagueWords.length === 0) return sentence

    // Sort by length descending so longer phrases match first
    const sorted = [...vagueWords].sort((a, b) => b.length - a.length)
    const escaped = sorted.map(w => w.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&'))
    const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
    const parts = sentence.split(regex)

    return parts.map((part, i) => {
        const lower = part.toLowerCase()
        if (vagueWords.some(w => w.toLowerCase() === lower)) {
            return <mark key={i} className="vague-highlight">{part}</mark>
        }
        return part
    })
}

export default function RequirementsTable({ requirements, nonRequirements }) {
    const [filter, setFilter] = useState('ALL')
    const [showNonReqs, setShowNonReqs] = useState(false)

    const filtered = useMemo(() => {
        if (filter === 'ALL') return requirements
        if (filter === 'VAGUE') return requirements.filter(r => r.is_vague)
        return requirements.filter(r => r.type === filter)
    }, [requirements, filter])

    const filters = [
        { key: 'ALL', label: '📋 All', count: requirements.length },
        { key: 'FR', label: '⚡ Functional', count: requirements.filter(r => r.type === 'FR').length },
        { key: 'NFR', label: '🛡️ Non-Functional', count: requirements.filter(r => r.type === 'NFR').length },
        { key: 'VAGUE', label: '⚠️ Vague', count: requirements.filter(r => r.is_vague).length },
    ]

    return (
        <>
            <div className="table-section">
                <h2 className="section-title">Requirements Breakdown</h2>
                <p className="section-sub">Click a filter to show specific requirement types. Vague words are highlighted in amber.</p>

                <div className="table-controls">
                    <div className="filter-btns">
                        {filters.map(f => (
                            <button
                                key={f.key}
                                className={`filter-btn ${filter === f.key ? `active-${f.key}` : ''}`}
                                onClick={() => setFilter(f.key)}
                                id={`filter-${f.key.toLowerCase()}`}
                            >
                                {f.label} <span style={{ opacity: 0.6, marginLeft: 4 }}>({f.count})</span>
                            </button>
                        ))}
                    </div>
                    <span className="count-badge">Showing {filtered.length} of {requirements.length}</span>
                </div>

                <div className="requirements-list" id="requirements-list">
                    {filtered.length === 0 ? (
                        <div className="empty-state">
                            <span className="empty-icon">🔍</span>
                            No requirements match this filter.
                        </div>
                    ) : (
                        filtered.map((req, idx) => (
                            <div
                                key={req.id}
                                className="req-card"
                                style={{ animationDelay: `${idx * 0.04}s` }}
                                id={`req-${req.id}`}
                            >
                                <span className="req-id">#{String(req.id).padStart(3, '0')}</span>

                                <div className="req-body">
                                    <p className="req-sentence">
                                        {highlightVagueWords(req.sentence, req.vague_words)}
                                    </p>

                                    {req.vague_words && req.vague_words.length > 0 && (
                                        <div className="vague-words-list">
                                            {req.vague_words.map((w, i) => (
                                                <span key={i} className="vague-tag">{w}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                <span className={`req-type-badge badge-${req.type}`}>{req.type}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {nonRequirements && nonRequirements.length > 0 && (
                <div className="non-reqs-section">
                    <button
                        className="btn btn-outline btn-sm"
                        onClick={() => setShowNonReqs(s => !s)}
                        id="toggle-non-reqs"
                        style={{ marginBottom: '16px' }}
                    >
                        {showNonReqs ? '▲ Hide' : '▼ Show'} Non-Requirement Sentences ({nonRequirements.length})
                    </button>
                    {showNonReqs && (
                        <div className="non-req-list">
                            {nonRequirements.map((item) => (
                                <div key={item.id} className="non-req-item">
                                    <span className="non-req-dot" />
                                    {item.sentence}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </>
    )
}
