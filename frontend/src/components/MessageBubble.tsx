import { ChatMessage } from "../types";
import PaperCard from "./PaperCard";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "../api";

interface Props {
  message: ChatMessage;
  onSummarize: (fileId: string) => void;
}

export default function MessageBubble({ message, onSummarize }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-3xl w-full ${isUser ? "flex justify-end" : ""}`}>
        <div
          className="px-4 py-3 rounded-2xl text-sm leading-relaxed"
          style={
            isUser
              ? { background: "#0f172a", color: "white", borderBottomRightRadius: "4px", maxWidth: "32rem" }
              : { background: "white", border: "1px solid #e2e8f0", color: "#1e293b", borderBottomLeftRadius: "4px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }
          }
        >
          {isUser ? (
            message.content
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-table:text-sm prose-td:px-3 prose-td:py-1 prose-th:px-3 prose-th:py-1">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && message.paper_groups && message.paper_groups.length > 0 && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {message.paper_groups.map((group, i) => (
              <PaperCard key={i} group={group} onSummarize={onSummarize} />
            ))}
          </div>
        )}

        {!isUser && message.resource_files && message.resource_files.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3">
            {message.resource_files.map((file, i) => (
              <a
                key={i}
                href={api.downloadUrl(file.file_id)}
                download
                className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-colors"
                style={{ background: "rgba(245,158,11,0.1)", color: "#92400e", border: "1px solid rgba(245,158,11,0.35)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(245,158,11,0.2)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(245,158,11,0.1)")}
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {file.subject ? `${file.subject}${file.level ? " " + file.level : ""} Data Booklet` : "Download Data Booklet"}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
