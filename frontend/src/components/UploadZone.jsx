import { useState, useRef, useCallback } from 'react'

const ALLOWED_EXTS = ['txt', 'docx']

function getExt(name) {
    return name?.split('.').pop()?.toLowerCase() || ''
}

export default function UploadZone({ onFileSelect, onError, selectedFile }) {
    const [isDragOver, setIsDragOver] = useState(false)
    const inputRef = useRef(null)

    const validateAndSelect = useCallback((file) => {
        if (!file) return
        const ext = getExt(file.name)
        if (!ALLOWED_EXTS.includes(ext)) {
            onError?.(`Unsupported format (.${ext || 'unknown'}). Please upload a .txt or .docx file.`)
            return
        }
        if (file.size > 5 * 1024 * 1024) {
            onError?.('File is too large. Maximum size is 5 MB.')
            return
        }
        onError?.(null)
        onFileSelect(file)
    }, [onFileSelect, onError])

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        setIsDragOver(false)
        const file = e.dataTransfer.files[0]
        validateAndSelect(file)
    }, [validateAndSelect])

    const handleDragOver = (e) => { e.preventDefault(); setIsDragOver(true) }
    const handleDragLeave = () => setIsDragOver(false)
    const handleInputChange = (e) => validateAndSelect(e.target.files[0])

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / 1048576).toFixed(1)} MB`
    }

    return (
        <div className="upload-section">
            <div
                className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
                onClick={() => inputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
                aria-label="Upload requirement document"
                id="upload-dropzone"
            >
                <span className="upload-icon">{selectedFile ? '✅' : '📄'}</span>
                <h2 className="upload-title">
                    {selectedFile ? 'Document Ready' : 'Drop your requirements document here'}
                </h2>
                <p className="upload-sub">
                    {selectedFile
                        ? 'Click to change file'
                        : 'Drag & drop a file or click to browse'
                    }
                </p>

                <div className="format-hint-pills">
                    <span className="format-pill format-txt">.TXT</span>
                    <span className="format-sep">·</span>
                    <span className="format-pill format-docx">.DOCX</span>
                    <span className="format-sep">supported · Max 5 MB</span>
                </div>

                <input
                    ref={inputRef}
                    type="file"
                    accept=".txt,.docx"
                    style={{ display: 'none' }}
                    onChange={handleInputChange}
                    id="file-input"
                />
            </div>

            {selectedFile && (
                <div className="file-selected-info">
                    <span className="file-icon">📎</span>
                    <span className="file-name">{selectedFile.name}</span>
                    <span className={`file-ext-badge ${getExt(selectedFile.name) === 'docx' ? 'badge-docx' : 'badge-txt'}`}>
                        .{getExt(selectedFile.name).toUpperCase()}
                    </span>
                    <span className="file-size">{formatSize(selectedFile.size)}</span>
                </div>
            )}
        </div>
    )
}
