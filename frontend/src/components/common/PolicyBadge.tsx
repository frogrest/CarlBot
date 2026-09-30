import React from 'react';
import { ShieldCheck, ShieldAlert, Shield, UserCheck } from 'lucide-react';
import type { SafetyClass } from '../../api/types';

interface PolicyBadgeProps {
  policyClass: SafetyClass | string;
  showIcon?: boolean;
  className?: string;
  actionName?: string;
}

export const PolicyBadge: React.FC<PolicyBadgeProps> = ({
  policyClass,
  showIcon = true,
  className = '',
  actionName,
}) => {
  const norm = (policyClass || '').toUpperCase();

  let badgeClass = 'policy-read';
  let label = norm;
  let icon = <Shield className="w-3 h-3 text-sky-400" />;

  switch (norm) {
    case 'READ':
      badgeClass = 'policy-read';
      label = 'READ';
      icon = <Shield className="w-3 h-3 text-sky-400" />;
      break;
    case 'SAFE_REVERSIBLE':
      badgeClass = 'policy-safe';
      label = 'SAFE / REVERSIBLE';
      icon = <ShieldCheck className="w-3 h-3 text-emerald-400" />;
      break;
    case 'APPROVAL_REQUIRED':
      badgeClass = 'policy-approval';
      label = 'APPROVAL REQUIRED';
      icon = <ShieldAlert className="w-3 h-3 text-amber-400" />;
      break;
    case 'HUMAN_ONLY':
      badgeClass = 'policy-human';
      label = 'HUMAN ONLY';
      icon = <UserCheck className="w-3 h-3 text-rose-400" />;
      break;
    default:
      label = norm || 'UNKNOWN';
  }

  return (
    <span
      className={`${badgeClass} ${className}`}
      title={actionName ? `Action: ${actionName} (${label})` : `Safety Policy: ${label}`}
    >
      {showIcon && icon}
      <span>{label}</span>
    </span>
  );
};
