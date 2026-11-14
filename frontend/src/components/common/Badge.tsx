import React from 'react';
import { clsx } from 'clsx';
import { CaseStatus, EvidenceType } from '../../types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'cyan' | 'purple';
  size?: 'sm' | 'md';
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className,
  dot = false,
}) => {
  const variantStyles = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    primary: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    danger: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  };

  const dotColors = {
    default: 'bg-slate-400',
    primary: 'bg-blue-400',
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    danger: 'bg-rose-400',
    cyan: 'bg-cyan-400',
    purple: 'bg-purple-400',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium rounded-full border',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {children}
    </span>
  );
};

export const CaseStatusBadge: React.FC<{ status: CaseStatus }> = ({ status }) => {
  switch (status) {
    case 'Active':
      return <Badge variant="success" dot>{status}</Badge>;
    case 'Under Review':
      return <Badge variant="warning" dot>{status}</Badge>;
    case 'Archived':
      return <Badge variant="default" dot>{status}</Badge>;
    case 'Closed':
      return <Badge variant="danger" dot>{status}</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
};

export const EvidenceTypeBadge: React.FC<{ type: EvidenceType }> = ({ type }) => {
  switch (type) {
    case 'image':
      return <Badge variant="purple" size="sm">IMAGE</Badge>;
    case 'audio':
      return <Badge variant="cyan" size="sm">AUDIO</Badge>;
    case 'document':
      return <Badge variant="primary" size="sm">DOC</Badge>;
    case 'text':
      return <Badge variant="warning" size="sm">TEXT/LOG</Badge>;
  }
};
