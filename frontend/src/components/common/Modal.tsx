import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { clsx } from 'clsx';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxW = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-stone-900/40 transition-opacity"
        onClick={onClose}
      />

      {/* Modal Surface */}
      <div
        className={clsx(
          'relative w-full bg-white border border-[#E6E4DF] rounded-md shadow-lg p-5 z-10 text-[#1C1917]',
          maxW[maxWidth]
        )}
      >
        {(title || description) && (
          <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-[#F0EFEB]">
            <div>
              {title && <h3 className="text-sm font-semibold text-[#1C1917]">{title}</h3>}
              {description && <p className="text-xs text-[#6B6862] mt-0.5">{description}</p>}
            </div>
            <button
              onClick={onClose}
              className="p-1 text-[#6B6862] hover:text-[#1C1917] rounded hover:bg-[#F5F5F0]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div>{children}</div>
      </div>
    </div>
  );
};
