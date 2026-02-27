import { PaperGroup } from "../types";
import { api } from "../api";

interface Props {
  group: PaperGroup;
  onSummarize: (fileId: string) => void;
}

const DIFFICULTY_STYLE: Record<string, { bg: string; color: string }> = {
  Easy:   { bg: "rgba(34,197,94,0.12)",  color: "#15803d" },
  Medium: { bg: "rgba(234,179,8,0.12)",  color: "#854d0e" },
  Hard:   { bg: "rgba(239,68,68,0.12)",  color: "#991b1b" },
};

export default function PaperCard({ group, onSummarize }: Props) {
  const { subject, level, year, session, paper, timezone, question_paper, markscheme, analysis } = group;

  const title = [subject, level, session, year, paper ? `Paper ${paper}` : null]
    .filter(Boolean)
    .join(" ");

  const diffStyle = analysis?.difficulty ? DIFFICULTY_STYLE[analysis.difficulty] : null;

  return (
    <div className="rounded-xl p-4 transition-shadow hover:shadow-md"
      style={{ background: "white", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
      {/* Title row */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-sm leading-snug" style={{ color: "#0f172a" }}>{title}</h3>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: "rgba(15,23,42,0.08)", color: "#0f172a" }}>
              {timezone}
            </span>
            {diffStyle && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                style={{ background: diffStyle.bg, color: diffStyle.color }}>
                {analysis!.difficulty}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Topic tags */}
      {analysis && analysis.topics.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-1">
          {analysis.topics.slice(0, 4).map((topic) => (
            <span key={topic} className="px-1.5 py-0.5 rounded text-xs"
              style={{ background: "rgba(99,102,241,0.08)", color: "#4338ca", border: "1px solid rgba(99,102,241,0.2)" }}>
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Section B topics */}
      {analysis && analysis.section_b_topics.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 mb-3">
          <span className="text-xs font-semibold" style={{ color: "#b45309" }}>Sec B:</span>
          {analysis.section_b_topics.slice(0, 3).map((topic) => (
            <span key={topic} className="px-1.5 py-0.5 rounded text-xs"
              style={{ background: "rgba(245,158,11,0.1)", color: "#92400e", border: "1px solid rgba(245,158,11,0.3)" }}>
              {topic}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {/* ── Question Paper column ── */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>
            Question Paper
          </p>
          {question_paper ? (
            <>
              <a
                href={api.downloadUrl(question_paper.file_id)}
                download
                className="flex items-center gap-1.5 w-full px-3 py-2 rounded-lg text-sm transition-colors"
                style={{ background: "rgba(15,23,42,0.05)", color: "#0f172a", border: "1px solid #e2e8f0" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(15,23,42,0.1)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(15,23,42,0.05)")}
              >
                <DownloadIcon />
                Download
              </a>
              <button
                onClick={() => onSummarize(question_paper.file_id)}
                className="flex items-center gap-1.5 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: "rgba(245,158,11,0.1)", color: "#92400e", border: "1px solid rgba(245,158,11,0.35)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(245,158,11,0.2)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(245,158,11,0.1)")}
              >
                <SparkleIcon />
                AI Summary
              </button>
            </>
          ) : (
            <p className="text-xs italic" style={{ color: "#cbd5e1" }}>Not available</p>
          )}
        </div>

        {/* ── Markscheme column ── */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>
            Markscheme
          </p>
          {markscheme ? (
            <a
              href={api.downloadUrl(markscheme.file_id)}
              download
              className="flex items-center gap-1.5 w-full px-3 py-2 rounded-lg text-sm transition-colors"
              style={{ background: "rgba(15,23,42,0.04)", color: "#1e293b", border: "1px solid #e2e8f0" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(15,23,42,0.1)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(15,23,42,0.04)")}
            >
              <CheckIcon />
              Download MS
            </a>
          ) : (
            <p className="text-xs italic" style={{ color: "#cbd5e1" }}>Not available</p>
          )}
        </div>
      </div>
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 00-1.098 2.653v1.5a.75.75 0 01-.75.75h-2.25a.75.75 0 01-.75-.75v-1.5a3.75 3.75 0 00-1.098-2.653L9.343 17.343z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
