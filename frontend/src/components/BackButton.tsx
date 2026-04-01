import { useNavigate } from 'react-router-dom';
import { useI18n } from '../i18n';

export default function BackButton() {
  const navigate = useNavigate();
  const { t } = useI18n();
  return (
    <button
      onClick={() => navigate(-1)}
      aria-label="Go back"
      className="flex flex-row items-center justify-center gap-2 pl-3 pr-4 py-2 rounded-lg border border-[#4285F4] bg-white text-[#4285F4] hover:bg-[#4285F4] hover:text-white transition-colors duration-150 whitespace-nowrap"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className="flex-shrink-0"
      >
        <path d="M19 12H5" />
        <path d="M12 5l-7 7 7 7" />
      </svg>
      <span className="text-sm font-semibold leading-none select-none">{t.backBtn}</span>
    </button>
  );
}
