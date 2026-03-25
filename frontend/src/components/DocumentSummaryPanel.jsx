function FileTypeBadge({ name }) {
    const ext = name?.split('.').pop()?.toUpperCase() || 'TXT'
    const color = ext === 'DOCX' ? 'badge-docx' : 'badge-txt'
    return <span className={`file-type-badge ${color}`}>.{ext}</span>
}

function MiniBar({ label, pct, colorClass }) {
    return (
        <div className="mini-bar-row">
            <span className="mini-bar-label">{label}</span>
            <div className="mini-bar-track">
                <div className={`mini-bar-fill ${colorClass}`} style={{ width: `${pct}%` }} />
            </div>
            <span className="mini-bar-pct">{pct}%</span>
        </div>
    )
}

export default function DocumentSummaryPanel({ file, metrics }) {
    const {
        total_sentences = 0,
        total_requirements = 0,
        fr_count = 0,
        nfr_count = 0,
        fr_percentage = 0,
        nfr_percentage = 0,
    } = metrics

    const reqs_pct = total_sentences > 0
        ? Math.round((total_requirements / total_sentences) * 100)
        : 0

    const formatSize = (bytes) => {
        if (!bytes) return '—'
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / 1048576).toFixed(1)} MB`
    }

    return (
        <div className="side-panel doc-summary-panel">
            <div className="panel-header">
                <span className="panel-header-icon">📄</span>
                <h3 className="panel-title">Document</h3>
            </div>

            <div className="doc-info-block">
                <FileTypeBadge name={file?.name} />
                <p className="doc-filename">{file?.name}</p>
                <p className="doc-filesize">{formatSize(file?.size)}</p>
            </div>

            <div className="panel-divider" />

            <div className="doc-stats">
                <div className="doc-stat-row">
                    <span className="doc-stat-label">Sentences Scanned</span>
                    <span className="doc-stat-value">{total_sentences}</span>
                </div>
                <div className="doc-stat-row">
                    <span className="doc-stat-label">Requirements Found</span>
                    <span className="doc-stat-value highlight-primary">{total_requirements}</span>
                </div>
                <div className="doc-stat-row">
                    <span className="doc-stat-label">Req. Coverage</span>
                    <span className="doc-stat-value">{reqs_pct}%</span>
                </div>
            </div>

            <div className="panel-divider" />

            <div className="panel-section-label">Requirement Split</div>
            <div className="mini-bars">
                <MiniBar label="FR" pct={fr_percentage} colorClass="fill-fr" />
                <MiniBar label="NFR" pct={nfr_percentage} colorClass="fill-nfr" />
            </div>

            <div className="panel-divider" />

            <div className="doc-counts-grid">
                <div className="doc-count-pill pill-fr">
                    <span className="pill-num">{fr_count}</span>
                    <span className="pill-label">Functional</span>
                </div>
                <div className="doc-count-pill pill-nfr">
                    <span className="pill-num">{nfr_count}</span>
                    <span className="pill-label">Non-Functional</span>
                </div>
            </div>
        </div>
    )
}
