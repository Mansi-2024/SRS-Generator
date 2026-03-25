function ScoreRing({ score }) {
    const radius = 44
    const circ = 2 * Math.PI * radius
    const offset = circ - (score / 100) * circ
    const color = score >= 90 ? '#16A34A' : score >= 75 ? '#2563EB' : score >= 55 ? '#F59E0B' : '#E11D48'

    return (
        <svg width="110" height="110" viewBox="0 0 110 110" style={{ display: 'block', margin: '0 auto' }}>
            <circle cx="55" cy="55" r={radius} fill="none" stroke="#E2E8F0" strokeWidth="10" />
            <circle
                cx="55" cy="55" r={radius} fill="none"
                stroke={color} strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={circ}
                strokeDashoffset={offset}
                style={{ transform: 'rotate(-90deg)', transformOrigin: '55px 55px', transition: 'stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1)' }}
            />
            <text x="55" y="51" textAnchor="middle" fill={color} fontSize="20" fontWeight="800" fontFamily="Inter, sans-serif">{score}</text>
            <text x="55" y="66" textAnchor="middle" fill="#94A3B8" fontSize="10" fontFamily="Inter, sans-serif">/ 100</text>
        </svg>
    )
}

export default function QualityPanel({ metrics, requirements }) {
    const {
        quality_score = 0,
        vague_count = 0,
        vague_percentage = 0,
    } = metrics

    const getGrade = (score) => {
        if (score >= 90) return { grade: 'A', label: 'Excellent', cls: 'grade-A' }
        if (score >= 75) return { grade: 'B', label: 'Good', cls: 'grade-B' }
        if (score >= 55) return { grade: 'C', label: 'Fair', cls: 'grade-C' }
        return { grade: 'D', label: 'Needs Work', cls: 'grade-D' }
    }

    const { grade, label, cls } = getGrade(quality_score)

    const vagueWords = [...new Set(
        (requirements || [])
            .filter(r => r.is_vague && r.vague_words)
            .flatMap(r => r.vague_words)
    )]

    const vagueReqs = (requirements || []).filter(r => r.is_vague)

    return (
        <div className="side-panel quality-panel">
            <div className="panel-header">
                <span className="panel-header-icon">🏆</span>
                <h3 className="panel-title">Quality Analysis</h3>
            </div>

            <div className="quality-ring-block">
                <ScoreRing score={quality_score} />
                <div style={{ textAlign: 'center', marginTop: '10px' }}>
                    <span className={`score-grade ${cls}`}>{grade} — {label}</span>
                </div>
            </div>

            <div className="panel-divider" />

            <div className="doc-stats">
                <div className="doc-stat-row">
                    <span className="doc-stat-label">Vague Requirements</span>
                    <span className="doc-stat-value" style={{ color: vague_count > 0 ? 'var(--vague-color)' : 'var(--fr-color)' }}>
                        {vague_count}
                    </span>
                </div>
                <div className="doc-stat-row">
                    <span className="doc-stat-label">Ambiguity Rate</span>
                    <span className="doc-stat-value" style={{ color: 'var(--vague-color)' }}>{vague_percentage}%</span>
                </div>
            </div>

            {vagueWords.length > 0 && (
                <>
                    <div className="panel-divider" />
                    <div className="panel-section-label">Ambiguous Terms</div>
                    <div className="vague-cloud">
                        {vagueWords.map((w, i) => (
                            <span key={i} className="vague-cloud-tag">{w}</span>
                        ))}
                    </div>
                </>
            )}

            {vagueReqs.length > 0 && (
                <>
                    <div className="panel-divider" />
                    <div className="panel-section-label">Needs Clarification</div>
                    <div className="clarify-list">
                        {vagueReqs.slice(0, 5).map(r => (
                            <div key={r.id} className="clarify-item">
                                <span className="clarify-dot" />
                                <span className="clarify-text">
                                    {r.sentence.length > 70 ? r.sentence.slice(0, 70) + '…' : r.sentence}
                                </span>
                            </div>
                        ))}
                        {vagueReqs.length > 5 && (
                            <p className="clarify-more">+{vagueReqs.length - 5} more vague requirements</p>
                        )}
                    </div>
                </>
            )}

            {vague_count === 0 && (
                <>
                    <div className="panel-divider" />
                    <div className="all-clear-badge">
                        <span>✅ No vague language detected</span>
                    </div>
                </>
            )}
        </div>
    )
}
