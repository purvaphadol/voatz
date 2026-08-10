import React from 'react';

/**
 * Animated toggle switch component for toggling active/inactive status.
 */
export function StatusToggle({ status, onToggle, disabled = false }) {
  const isActive = status === 1 || status === '1' || status === 'active' || status === 'ACTIVE';

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onToggle && onToggle(!isActive)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        isActive ? 'bg-indigo-600' : 'bg-slate-700'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          isActive ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

export default StatusToggle;
