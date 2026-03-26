import { useCallback, useRef, useState } from 'react';
import { useI18n } from '../i18n';

interface Props {
  accept?: string;
  multiple?: boolean;
  label: string;
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export default function FileUpload({ accept = '.pdf,.docx', multiple = false, label, onFiles, disabled }: Props) {
  const { t } = useI18n();
  const [dragOver, setDragOver] = useState(false);
  // Local "busy" gate — prevents further input while an upload is in flight,
  // even if the parent hasn't set disabled=true yet (e.g. the instant after drop).
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const isDisabled = disabled || busy;

  const dispatch = useCallback(
    async (files: File[]) => {
      if (!files.length || isDisabled) return;
      // Immediately lock the zone and blur the input to dismiss the file picker
      setBusy(true);
      if (inputRef.current) {
        inputRef.current.value = '';
        inputRef.current.blur();
      }
      try {
        await Promise.resolve(onFiles(files));
      } finally {
        setBusy(false);
      }
    },
    [onFiles, isDisabled],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      // Best-effort: bring the browser window to the front to push the OS file
      // picker dialog behind it (browser security prevents programmatic close).
      window.focus();
      dispatch(Array.from(e.dataTransfer.files));
    },
    [dispatch],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      dispatch(Array.from(e.target.files ?? []));
    },
    [dispatch],
  );

  // Visual collapse: file received → zone transforms into a slim processing bar.
  // This mirrors the OS dialog closing when a file is selected via click.
  if (isDisabled) {
    return (
      <div className="border-2 border-dashed border-indigo-200 rounded-lg px-5 py-3.5 flex items-center gap-3 bg-indigo-50/60 transition-all">
        <svg
          className="animate-spin h-4 w-4 text-indigo-400 flex-shrink-0"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span className="text-sm text-indigo-500 font-medium">{t.fileUploading}</span>
      </div>
    );
  }

  return (
    <label
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`
        block border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
        ${dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 hover:border-indigo-300'}
      `}
    >
      <p className="text-gray-600 font-medium">{label}</p>
      <p className="text-sm text-gray-400 mt-1">{t.dragHint}</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        disabled={isDisabled}
        className="hidden"
      />
    </label>
  );
}
