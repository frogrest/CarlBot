import React, { useState } from 'react';
import { AlertTriangle, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  error?: any;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to load service data',
  message = 'The service did not respond or returned an error.',
  error,
  onRetry,
  className = '',
}) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className={`p-6 rounded-lg bg-rose-950/20 border border-rose-900/40 text-slate-200 ${className}`}>
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-rose-900/40 text-rose-400 mt-0.5">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-rose-300">{title}</h4>
          <p className="text-sm text-slate-300 mt-1">{message}</p>

          <div className="mt-4 flex items-center gap-3">
            {onRetry && (
              <button
                onClick={onRetry}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium bg-rose-900/50 hover:bg-rose-800/60 text-white border border-rose-700/60 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </button>
            )}

            {error && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200"
              >
                {showDetails ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                Technical details
              </button>
            )}
          </div>

          {showDetails && error && (
            <pre className="mt-3 p-3 rounded bg-slate-950/80 border border-slate-800 text-[11px] font-mono text-slate-400 overflow-x-auto max-h-40">
              {typeof error === 'string' ? error : JSON.stringify(error, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};
