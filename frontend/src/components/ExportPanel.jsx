import { useState } from 'react'

const FIELD_STYLE = { display: 'flex', flexDirection: 'column', gap: '6px' }
const INPUT_STYLE = {
    background: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '8px',
    color: '#0F172A',
    fontFamily: 'var(--font-body)',
    fontSize: '0.88rem',
    padding: '9px 14px',
    outline: 'none',
    transition: 'border-color 0.2s',
    width: '100%',
}
const LABEL_STYLE = {
    fontSize: '0.75rem',
    fontWeight: '600',
    color: '#64748B',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
}

function MetaInput({ id, label, value, onChange, placeholder }) {
    return (
        <div style={FIELD_STYLE}>
            <label htmlFor={id} style={LABEL_STYLE}>{label}</label>
            <input
                id={id}
                style={INPUT_STYLE}
                value={value}
                onChange={e => onChange(e.target.value)}
                placeholder={placeholder}
                onFocus={e => (e.target.style.borderColor = '#2563EB')}
                onBlur={e => (e.target.style.borderColor = '#E2E8F0')}
            />
        </div>
    )
}

const FORMATS = [
    { key: 'txt',  label: 'TXT',  icon: '📄', desc: 'Plain text with preview' },
    { key: 'docx', label: 'DOCX', icon: '📝', desc: 'Microsoft Word document' },
    { key: 'pdf',  label: 'PDF',  icon: '📕', desc: 'Portable Document Format' },
]

export default function ExportPanel({ analysisData }) {
    const [srsText, setSrsText] = useState(null)
    const [loading, setLoading] = useState(false)
    const [showModal, setShowModal] = useState(false)
    const [error, setError] = useState(null)
    const [showForm, setShowForm] = useState(false)
    const [format, setFormat] = useState('txt')

    const today = new Date().toISOString().split('T')[0]
    const [projectName, setProjectName] = useState('')
    const [author, setAuthor] = useState('')
    const [organization, setOrganization] = useState('')
    const [version, setVersion] = useState('1.0')
    const [dateCreated, setDateCreated] = useState(today)

    const payload = () => ({
        ...analysisData,
        project_name: projectName || '<Project>',
        author:       author || '<author>',
        organization: organization || '<organization>',
        version:      version || '1.0',
        date_created: dateCreated || today,
    })

    const buildFilename = (ext) => {
        const safe = (projectName || 'Project').replace(/\s+/g, '_')
        return `SRS_${safe}_IEEE830.${ext}`
    }

    const fetchSRS = async () => {
        setLoading(true)
        setError(null)
        setSrsText(null)

        try {
            const res = await fetch(`/api/export?format=${format}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload()),
            })

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}))
                throw new Error(errData.error || 'Export failed.')
            }

            if (format === 'txt') {
                const data = await res.json()
                setSrsText(data.srs)
                setShowModal(true)
            } else {
                const blob = await res.blob()
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = buildFilename(format)
                document.body.appendChild(a)
                a.click()
                a.remove()
                URL.revokeObjectURL(url)
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const downloadTxt = () => {
        if (!srsText) return
        const blob = new Blob([srsText], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = buildFilename('txt')
        a.click()
        URL.revokeObjectURL(url)
    }

    const copyToClipboard = () => {
        if (srsText) navigator.clipboard.writeText(srsText)
    }

    const selectedFmt = FORMATS.find(f => f.key === format)

    return (
        <>
            <div className="export-section">
                <h2 className="section-title">Export IEEE 830 SRS</h2>
                <p className="section-sub">
                    Generate a complete IEEE 830-1998 Software Requirements Specification document
                </p>

                <div className="export-card" style={{ flexDirection: 'column', gap: '24px' }}>
                    {/* Header row */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '24px', flexWrap: 'wrap', width: '100%' }}>
                        <div className="export-info" style={{ flex: 1, minWidth: '220px' }}>
                            <h3 className="export-title">📑 IEEE 830-1998 SRS Document</h3>
                            <p className="export-desc">
                                Generates a full six-section SRS with Appendices A–C and an
                                Ambiguity/TBD report. Follows the Karl E. Wiegers template.
                            </p>
                        </div>
                        <button
                            className="btn btn-outline btn-sm"
                            onClick={() => setShowForm(f => !f)}
                            id="toggle-metadata-btn"
                        >
                            {showForm ? '▲ Hide' : '⚙️ Set'} Project Info
                        </button>
                    </div>

                    {/* Metadata form */}
                    {showForm && (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                            gap: '16px', width: '100%', padding: '20px',
                            background: '#F8FAFC', borderRadius: '8px',
                            border: '1px solid #E2E8F0',
                        }}>
                            <MetaInput id="meta-project" label="Project Name" value={projectName}
                                onChange={setProjectName} placeholder="e.g. E-Commerce Platform" />
                            <MetaInput id="meta-author" label="Prepared By" value={author}
                                onChange={setAuthor} placeholder="e.g. John Smith" />
                            <MetaInput id="meta-org" label="Organization" value={organization}
                                onChange={setOrganization} placeholder="e.g. Acme Corp" />
                            <MetaInput id="meta-version" label="Version" value={version}
                                onChange={setVersion} placeholder="1.0" />
                            <MetaInput id="meta-date" label="Date" value={dateCreated}
                                onChange={setDateCreated} placeholder="YYYY-MM-DD" />
                        </div>
                    )}

                    {/* Format selector */}
                    <div style={{ width: '100%' }}>
                        <p style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px' }}>
                            Export Format
                        </p>
                        <div className="format-selector">
                            {FORMATS.map(f => (
                                <button
                                    key={f.key}
                                    className={`format-btn ${format === f.key ? 'format-btn-active' : ''}`}
                                    onClick={() => setFormat(f.key)}
                                    id={`format-${f.key}`}
                                >
                                    <span className="format-btn-icon">{f.icon}</span>
                                    <span className="format-btn-label">{f.label}</span>
                                    <span className="format-btn-desc">{f.desc}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Action buttons */}
                    <div className="export-actions" style={{ width: '100%' }}>
                        <button
                            id="generate-srs-btn"
                            className="btn btn-primary"
                            onClick={fetchSRS}
                            disabled={loading}
                        >
                            {loading
                                ? <><span className="spinner" /> Generating {selectedFmt?.label}…</>
                                : `📑 Generate ${selectedFmt?.label} SRS`
                            }
                        </button>
                        {srsText && format === 'txt' && (
                            <button id="download-srs-btn" className="btn btn-success" onClick={downloadTxt}>
                                ⬇️ Download TXT
                            </button>
                        )}
                    </div>

                    {format !== 'txt' && (
                        <div className="export-info-note">
                            💡 {selectedFmt?.label} files will download automatically after generation.
                        </div>
                    )}
                </div>

                {error && (
                    <div className="error-banner" style={{ marginTop: '16px' }}>
                        ⚠️ {error}
                    </div>
                )}
            </div>

            {/* SRS Preview Modal (TXT only) */}
            {showModal && srsText && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal-box" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <span className="modal-title">
                                📄 IEEE 830-1998 SRS — {projectName || '<Project>'}
                            </span>
                            <button className="modal-close" onClick={() => setShowModal(false)} id="close-modal">✕</button>
                        </div>
                        <div className="modal-body">
                            <pre className="srs-preview">{srsText}</pre>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-outline btn-sm" onClick={copyToClipboard} id="copy-srs">
                                📋 Copy
                            </button>
                            <button className="btn btn-success btn-sm" onClick={downloadTxt} id="download-from-modal">
                                ⬇️ Download TXT
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
