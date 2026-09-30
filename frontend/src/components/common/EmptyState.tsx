import React from 'react';
import { ShieldCheck } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No active incidents',
  description = 'All monitored systems are currently healthy.',
  icon,
  action,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center bg-surface-subtle/50 rounded-lg border border-dashed border-surface-border ${className}`}>
      <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-300 mb-3">
        {icon || <ShieldCheck className="w-6 h-6 text-emerald-400" />}
      </div>
      <h4 className="text-base font-medium text-slate-200">{title}</h4>
      <p className="text-sm text-slate-400 mt-1 max-w-md">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
