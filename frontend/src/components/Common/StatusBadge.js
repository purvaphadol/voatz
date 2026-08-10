import React from 'react';

/**
 * Modern Status Badge pill rendering ACTIVE, INACTIVE, or DELETED states.
 */
export function StatusBadge({ status, activeLabel = 'ACTIVE', inactiveLabel = 'INACTIVE', deletedLabel = 'DELETED' }) {
  const getBadgeStyle = () => {
    switch (status) {
      case 1:
      case '1':
      case 'active':
      case 'ACTIVE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 dot-emerald';
      case 0:
      case '0':
      case 'inactive':
      case 'INACTIVE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20 dot-amber';
      case 9:
      case '9':
      case 'deleted':
      case 'DELETED':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20 dot-rose';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20 dot-slate';
    }
  };

  const getLabel = () => {
    switch (status) {
      case 1:
      case '1':
      case 'active':
      case 'ACTIVE':
        return activeLabel;
      case 0:
      case '0':
      case 'inactive':
      case 'INACTIVE':
        return inactiveLabel;
      case 9:
      case '9':
      case 'deleted':
      case 'DELETED':
        return deletedLabel;
      default:
        return String(status || 'UNKNOWN');
    }
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getBadgeStyle()}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {getLabel()}
    </span>
  );
}

export default StatusBadge;
