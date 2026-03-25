export default function MetricsPanel({ metrics }) {
    const {
        total_requirements = 0,
        fr_count = 0,
        nfr_count = 0,
        vague_count = 0,
        fr_percentage = 0,
        nfr_percentage = 0,
        vague_percentage = 0,
        quality_score = 0,
    } = metrics

    const getGrade = (score) => {
        if (score >= 90) return { grade: 'A', label: 'Excellent' }
        if (score >= 75) return { grade: 'B', label: 'Good' }
        if (score >= 55) return { grade: 'C', label: 'Fair' }
        return { grade: 'D', label: 'Needs Work' }
    }

    const { grade, label } = getGrade(quality_score)

    return (
        <div className="metrics-section">
            <h2 className="section-title">Quality Metrics</h2>
            <p className="section-sub">Overview of your requirements document quality</p>

            <div className="metrics-grid">
                {/* Total */}
                <div className="metric-card card-total">
                    <span className="metric-icon">📊</span>
                    <span className="metric-label">Total Requirements</span>
                    <span className="metric-value">{total_requirements}</span>
                    <div className="progress-bar-wrapper">
                        <div className="progress-item">
                            <span className="progress-label">FR</span>
                            <div className="progress-track">
                                <div className="progress-fill fill-fr" style={{ width: `${fr_percentage}%` }} />
                            </div>
                            <span className="progress-pct">{fr_percentage}%</span>
                        </div>
                        <div className="progress-item">
                            <span className="progress-label">NFR</span>
                            <div className="progress-track">
                                <div className="progress-fill fill-nfr" style={{ width: `${nfr_percentage}%` }} />
                            </div>
                            <span className="progress-pct">{nfr_percentage}%</span>
                        </div>
                    </div>
                </div>

                {/* FR */}
                <div className="metric-card card-fr">
                    <span className="metric-icon">⚡</span>
                    <span className="metric-label">Functional</span>
                    <span className="metric-value">{fr_count}</span>
                    <span className="metric-pct">{fr_percentage}% of requirements</span>
                </div>

                {/* NFR */}
                <div className="metric-card card-nfr">
                    <span className="metric-icon">🛡️</span>
                    <span className="metric-label">Non-Functional</span>
                    <span className="metric-value">{nfr_count}</span>
                    <span className="metric-pct">{nfr_percentage}% of requirements</span>
                </div>

                {/* Vague */}
                <div className="metric-card card-vague">
                    <span className="metric-icon">⚠️</span>
                    <span className="metric-label">Vague</span>
                    <span className="metric-value">{vague_count}</span>
                    <span className="metric-pct">{vague_percentage}% contain ambiguity</span>
                </div>

                {/* Quality Score */}
                <div className="metric-card card-score">
                    <span className="metric-icon">🏆</span>
                    <span className="metric-label">Quality Score</span>
                    <div className="score-ring-wrapper">
                        <span className="metric-value" style={{ fontSize: '3rem' }}>{quality_score}</span>
                        <div className="score-ring-label">
                            <span style={{ color: 'var(--text-muted)', fontSize: '1rem', fontWeight: 600 }}>/100</span>
                            <span className={`score-grade grade-${grade}`}>{grade} — {label}</span>
                        </div>
                    </div>
                    <div style={{ height: '5px', borderRadius: '100px', background: '#E2E8F0', overflow: 'hidden', marginTop: '8px' }}>
                        <div
                            style={{
                                height: '100%',
                                borderRadius: '100px',
                                background: 'linear-gradient(90deg, #2563EB, #7C3AED)',
                                width: `${quality_score}%`,
                                transition: 'width 1s cubic-bezier(0.4, 0, 0.2, 1)',
                            }}
                        />
                    </div>
                </div>
            </div>
        </div>
    )
}
