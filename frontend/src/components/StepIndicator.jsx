export default function StepIndicator({ currentStep }) {
    const steps = [
        { n: 1, label: 'Upload Document', icon: '📤' },
        { n: 2, label: 'Analyze', icon: '🔬' },
        { n: 3, label: 'Review Requirements', icon: '📋' },
        { n: 4, label: 'Generate SRS', icon: '📑' },
    ]

    return (
        <div className="step-indicator-wrapper">
            <div className="step-indicator">
                {steps.map((step, i) => {
                    const isCompleted = currentStep > step.n
                    const isActive = currentStep === step.n
                    return (
                        <div key={step.n} className="step-item">
                            {i > 0 && (
                                <div className={`step-connector ${isCompleted || currentStep > step.n - 1 ? 'connector-done' : ''}`} />
                            )}
                            <div className={`step-circle ${isActive ? 'step-active' : ''} ${isCompleted ? 'step-done' : ''}`}>
                                {isCompleted ? '✓' : step.icon}
                            </div>
                            <span className={`step-label ${isActive ? 'label-active' : ''} ${isCompleted ? 'label-done' : ''}`}>
                                {step.label}
                            </span>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
