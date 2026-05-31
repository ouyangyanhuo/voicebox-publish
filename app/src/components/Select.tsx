import { ChevronDown } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

export type SelectOption = {
  value: string;
  label: string;
};

type SelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  width?: number | string;
  disabled?: boolean;
  className?: string;
};

export function Select({ value, onChange, options, width, disabled, className }: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const handle = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [open, close]);

  useEffect(() => {
    if (!open) return;
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const idx = options.findIndex((o) => o.value === value);
        const next = e.key === 'ArrowDown'
          ? Math.min(idx + 1, options.length - 1)
          : Math.max(idx - 1, 0);
        onChange(options[next].value);
      }
    };
    document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, [open, close, options, value, onChange]);

  return (
    <div
      ref={ref}
      className={`select-wrap${className ? ` ${className}` : ''}${disabled ? ' disabled' : ''}`}
      style={width ? { width } : undefined}
    >
      <button
        type="button"
        className="select-trigger"
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="select-value">{selected?.label ?? ''}</span>
        <ChevronDown size={14} className={`select-chevron${open ? ' open' : ''}`} />
      </button>
      {open && (
        <div className="select-dropdown" role="listbox">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="option"
              aria-selected={opt.value === value}
              className={`select-option${opt.value === value ? ' selected' : ''}`}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(opt.value);
                close();
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
