import React from 'react';

const STAGES = [
  { id: 'source', label: 'Input source', href: '#tier-1' },
  { id: 'analysis', label: 'Repository analyzer', href: '#tier-1' },
  { id: 'generation', label: 'Infrastructure generation', href: '#tier-2' },
  { id: 'validation', label: 'Validation & repair', href: '#tier-3' },
  { id: 'readiness', label: 'Readiness & scoring', href: '#tier-4' },
  { id: 'deployment', label: 'Kubernetes target', href: '#tier-4' },
];

const STATUS_COLORS = {
  pending: 'var(--aws-muted)',      // slate-500
  running: 'var(--aws-link)',      // blue-500
  passed: 'var(--aws-success)',       // emerald-400
  failed: 'var(--aws-error)',       // red-400
  'needs-review': 'var(--aws-warning)', // amber-400
};

const STATUS_ICONS = {
  pending: '·',
  running: '↻',
  passed: '✓',
  failed: '×',
  'needs-review': '!',
};

export default function PipelineVisualizer({ statuses = {} }) {
  // statuses is a map of stage_id -> 'pending' | 'running' | 'passed' | 'failed' | 'needs-review'
  
  return (
    <div className="card workflow-overview" style={{ marginBottom: '2rem', padding: '1.5rem', overflowX: 'auto' }}>
      <div className="workflow-overview-heading">
        <div>
          <p className="aws-eyebrow">End-to-end workflow</p>
          <h2>From code to production</h2>
        </div>
        <span>6 stages · 4 tiers</span>
      </div>
      
      <div className="workflow-stage-row">
        {STAGES.map((stage, index) => {
          const status = statuses[stage.id] || 'pending';
          const color = STATUS_COLORS[status];
          const icon = STATUS_ICONS[status];
          const isLast = index === STAGES.length - 1;

          return (
            <React.Fragment key={stage.id}>
              {/* Node */}
              <a href={stage.href} className="workflow-stage" key={stage.id}>
                <div 
                  title={`${stage.label} - ${status.toUpperCase()}`}
                  style={{
                    width: '32px', height: '32px', borderRadius: '50%',
                    background: status === 'pending' ? 'transparent' : 'var(--aws-panel)',
                    border: `2px solid ${color}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.8rem',
                    boxShadow: 'none',
                    color,
                    fontWeight: 700,
                    zIndex: 2,
                  }}
                >
                  {status === 'pending' ? <span style={{ width: 7, height: 7, borderRadius: '50%', background: color }} /> : icon}
                </div>
                <span className="workflow-stage-label">{stage.label}</span>
              </a>
              
              {/* Edge */}
              {!isLast && (
                <div className="workflow-stage-edge">
                  <div style={{ 
                    height: '100%', 
                    background: status === 'passed' ? STATUS_COLORS.passed : 'transparent',
                    width: status === 'passed' ? '100%' : '0%',
                    transition: 'width 0.5s ease'
                  }} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
