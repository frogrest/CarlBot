import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Wrench, Clock, HelpCircle } from 'lucide-react';

export type StatusVariant =
  | 'healthy'
  | 'warning'
  | 'investigating'
  | 'technician'
  | 'critical'
  | 'unknown';

interface BadgeProps {
  status: StatusVariant | string;
  label?: string;
  showIcon?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  status,
  label,
  showIcon = true,
  className = '',
}) => {
  const normStatus = (status || 'unknown').toLowerCase();

  let variant: StatusVariant = 'unknown';
  let defaultLabel = status;
  let icon = <HelpCircle className="w-3 h-3" />;
  let badgeClass = 'badge-unknown';

  if (['healthy', 'resolved', 'up', 'online', 'pass'].includes(normStatus)) {
    variant = 'healthy';
    defaultLabel = label || 'Healthy';
    icon = <CheckCircle2 className="w-3 h-3 text-emerald-400" />;
    badgeClass = 'badge-healthy';
  } else if (['warning', 'pending_approval', 'degraded'].includes(normStatus)) {
    variant = 'warning';
    defaultLabel = label || 'Warning';
    icon = <AlertTriangle className="w-3 h-3 text-amber-400" />;
    badgeClass = 'badge-warning';
  } else if (['investigating', 'open', 'in_progress', 'running'].includes(normStatus)) {
    variant = 'investigating';
    defaultLabel = label || 'Investigating';
    icon = <Clock className="w-3 h-3 text-sky-400 animate-pulse" />;
    badgeClass = 'badge-investigating';
  } else if (['technician', 'pending_technician', 'technician_required', 'escalated'].includes(normStatus)) {
    variant = 'technician';
    defaultLabel = label || 'Tech Required';
    icon = <Wrench className="w-3 h-3 text-orange-400" />;
    badgeClass = 'badge-technician';
  } else if (['critical', 'down', 'fail', 'failed', 'blocked'].includes(normStatus)) {
    variant = 'critical';
    defaultLabel = label || 'Critical';
    icon = <AlertCircle className="w-3 h-3 text-rose-400" />;
    badgeClass = 'badge-critical';
  }

  return (
    <span className={`${badgeClass} ${className}`} data-variant={variant}>
      {showIcon && icon}
      <span>{label || defaultLabel}</span>
    </span>
  );
};
