import { useState, useRef } from 'react'
import UploadZone from './components/UploadZone'
import MetricsPanel from './components/MetricsPanel'
import RequirementsEditor from './components/RequirementsEditor'
import ExportPanel from './components/ExportPanel'
import StepIndicator from './components/StepIndicator'
import DocumentSummaryPanel from './components/DocumentSummaryPanel'
import QualityPanel from './components/QualityPanel'
import './index.css'

export default function App() {
    const [selectedFile, setSelectedFile]               = useState(null)
    const [analysisData, setAnalysisData]               = useState(null)
    const [editableRequirements, setEditableRequirements] = useState([])
    const [loading, setLoading]                         = useState(false)
    const [error, setError]                             = useState(null)
    const [currentStep, setCurrentStep]                 = useState(1)
    const resultsRef = useRef(null)

    const handleFileSelect = (file) => {
        setSelectedFile(file)
        setError(null)
        setCurrentStep(2)
    }

    const handleFileError = (msg) => {
        setError(msg)
        setSelectedFile(null)
        setCurrentStep(1)
    }

    const handleAnalyze = async () => {
        if (!selectedFile) return
        setLoading(true)
        setError(null)
        setAnalysisData(null)
        setEditableRequirements([])

        const formData = new FormData()
        formData.append('file', selectedFile)

        try {
            const res = await fetch('/api/analyze', { method: 'POST', body: formData })
            const data = await res.json()
            if (!res.ok) throw new Error(data.error || 'Analysis failed.')
            setAnalysisData(data)
            // Initialize editable requirements from analysis result
            setEditableRequirements(data.requirements || [])
            setCurrentStep(3)
            setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
        } catch (err) {
            setError(err.message)
            setCurrentStep(2)
        } finally {
            setLoading(false)
        }
    }

    const handleReset = () => {
        setSelectedFile(null)
        setAnalysisData(null)
        setEditableRequirements([])
        setError(null)
        setCurrentStep(1)
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    // Derive metrics from editable requirements so panels stay in sync
    const liveMetrics = analysisData ? {
        ...analysisData.metrics,
        fr_count:    editableRequirements.filter(r => r.type === 'FR').length,
        nfr_count:   editableRequirements.filter(r => r.type === 'NFR').length,
        vague_count: editableRequirements.filter(r => r.is_vague).length,
        total_requirements: editableRequirements.length,
        fr_percentage:  editableRequirements.length
            ? Math.round(editableRequirements.filter(r=>r.type==='FR').length / editableRequirements.length * 100)
            : 0,
        nfr_percentage: editableRequirements.length
            ? Math.round(editableRequirements.filter(r=>r.type==='NFR').length / editableRequirements.length * 100)
            : 0,
        vague_percentage: editableRequirements.length
            ? Math.round(editableRequirements.filter(r=>r.is_vague).length / editableRequirements.length * 100)
            : 0,
    } : null

    // Build the data payload for export — always use the edited requirements
    const exportPayload = analysisData ? {
        ...analysisData,
        requirements: editableRequirements,
        metrics: liveMetrics,
    } : null

    return (
        <div className="app-wrapper">
            {/* Loading Overlay */}
            {loading && (
                <div className="loading-overlay">
                    <div className="loading-card">
                        <div className="loading-spinner-ring" />
                        <p className="loading-title">Analyzing Requirements…</p>
                        <p className="loading-sub">NLP pipeline is extracting and classifying your requirements</p>
                        <div className="loading-steps">
                            {['Parsing sentences', 'Classifying FR / NFR', 'Detecting vague words', 'Computing quality score'].map((s, i) => (
                                <div key={i} className="loading-step-item" style={{ animationDelay: `${i * 0.4}s` }}>
                                    <span className="loading-step-dot" />
                                    {s}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Navbar */}
            <nav className="navbar">
                <div className="container navbar-inner">
                    <a href="/" className="logo">
                        <div className="logo-icon">🔬</div>
                        <span className="logo-text">ARAQAT</span>
                    </a>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className="nav-badge">NLP Powered</span>
                        {analysisData && (
                            <button className="btn btn-outline btn-sm" onClick={handleReset} id="reset-btn">
                                ↩ New Analysis
                            </button>
                        )}
                    </div>
                </div>
            </nav>

            <main className="container">
                {/* Hero */}
                <section className="hero">
                    <div className="hero-tag">✨ Automated Analysis</div>
                    <h1 className="hero-title">
                        Analyze Your{' '}
                        <span className="gradient-text">Requirements Document</span>{' '}
                        with NLP
                    </h1>
                    <p className="hero-subtitle">
                        Upload your requirements, review and edit extracted items, then generate a
                        complete IEEE 830-1998 SRS — automatically.
                    </p>
                    <div className="feature-pills">
                        {[
                            { icon: '📤', label: 'Upload .txt or .docx' },
                            { icon: '⚡', label: 'FR/NFR classification' },
                            { icon: '✏️', label: 'Inline requirement editing' },
                            { icon: '⚠️', label: 'Vague word detection' },
                            { icon: '📊', label: 'Quality scoring' },
                            { icon: '📑', label: 'SRS export (TXT/DOCX/PDF)' },
                        ].map((f, i) => (
                            <span key={i} className="feature-pill">{f.icon} {f.label}</span>
                        ))}
                    </div>
                </section>

                {/* Step Indicator */}
                <StepIndicator currentStep={currentStep} />

                {/* Upload Phase */}
                {!analysisData && (
                    <div className="upload-phase">
                        <UploadZone
                            onFileSelect={handleFileSelect}
                            onError={handleFileError}
                            selectedFile={selectedFile}
                        />

                        {error && <div className="error-banner">⚠️ {error}</div>}

                        <div style={{ textAlign: 'center', marginBottom: '60px' }}>
                            <button
                                id="analyze-btn"
                                className="btn btn-primary"
                                onClick={handleAnalyze}
                                disabled={!selectedFile || loading}
                                style={{ minWidth: '240px', fontSize: '1.05rem', padding: '16px 36px' }}
                            >
                                🔬 Analyze Requirements
                            </button>
                            {selectedFile && (
                                <p style={{ marginTop: '12px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                                    Ready to analyze <strong style={{ color: 'var(--accent-emerald)' }}>{selectedFile.name}</strong>
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {/* Results Phase */}
                {analysisData && (
                    <div ref={resultsRef}>
                        {/* Status bar */}
                        <div className="reset-bar" style={{ borderRadius: 'var(--radius-md)', marginBottom: '28px' }}>
                            <div className="reset-bar-info">
                                <span className="file-dot" />
                                <span>
                                    <strong style={{ color: 'var(--accent-emerald)' }}>{selectedFile?.name}</strong>
                                    {' '}— {editableRequirements.length} requirements
                                    {editableRequirements.length !== analysisData.requirements?.length &&
                                        <span style={{ color: 'var(--accent-amber)', marginLeft: 6 }}>
                                            (edited from {analysisData.requirements?.length})
                                        </span>
                                    }
                                </span>
                            </div>
                            <button id="analyze-new-btn" className="btn btn-outline btn-sm" onClick={handleReset}>
                                ↩ New Analysis
                            </button>
                        </div>

                        {/* Live metrics row */}
                        <div style={{ marginBottom: '28px' }}>
                            <MetricsPanel metrics={liveMetrics} />
                        </div>

                        {/* 3-column layout */}
                        <div className="results-layout">
                            {/* Left: Document Summary */}
                            <div className="panel-left">
                                <DocumentSummaryPanel file={selectedFile} metrics={liveMetrics} />
                            </div>

                            {/* Center: Editable Requirements */}
                            <div className="panel-center">
                                <RequirementsEditor
                                    requirements={editableRequirements}
                                    setRequirements={setEditableRequirements}
                                    nonRequirements={analysisData.non_requirements}
                                />
                            </div>

                            {/* Right: Quality Panel */}
                            <div className="panel-right">
                                <QualityPanel
                                    metrics={liveMetrics}
                                    requirements={editableRequirements}
                                />
                            </div>
                        </div>

                        {/* Export */}
                        <div style={{ marginTop: '36px' }} onClick={() => setCurrentStep(4)}>
                            <ExportPanel analysisData={exportPayload} />
                        </div>
                    </div>
                )}
            </main>

            <footer className="footer">
                <div className="container">
                    ARAQAT — Automated Requirements Analysis &amp; Quality Assessment Tool &nbsp;·&nbsp;
                    Built with React + Flask + spaCy
                </div>
            </footer>
        </div>
    )
}
