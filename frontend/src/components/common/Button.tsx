import React from 'react';
import { clsx } from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  disabled,
  ...props
}) => {
  const base = 'inline-flex items-center justify-center font-medium rounded transition-colors text-sm focus:outline-none focus:ring-1 focus:ring-offset-1 select-none disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-[#0F766E] hover:bg-[#115E59] text-white focus:ring-[#0F766E]',
    secondary: 'bg-white hover:bg-[#F5F5F0] text-[#1C1917] border border-[#E6E4DF] focus:ring-stone-400',
    danger: 'bg-stone-100 hover:bg-rose-50 text-rose-700 border border-rose-200 focus:ring-rose-400',
    ghost: 'bg-transparent hover:bg-[#F0EFEB] text-[#6B6862] hover:text-[#1C1917] focus:ring-stone-400',
  };

  const sizes = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-xs px-3.5 py-2 gap-2',
  };

  return (
    <button
      className={clsx(base, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {children}
    </button>
  );
};
