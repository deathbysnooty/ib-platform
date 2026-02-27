export interface User {
  email: string;
  name: string;
  picture?: string;
}

export interface PaperFile {
  file_id: string;
  filename: string;
  subject?: string;
  level?: string;
  year?: number;
  session?: string;
  paper?: number;
  timezone?: string;
  type: "question" | "markscheme" | "data_booklet";
}

export interface PaperAnalysis {
  difficulty?: string;
  topics: string[];
  section_b_topics: string[];
}

export interface PaperGroup {
  subject: string;
  level?: string;
  year?: number;
  session?: string;
  paper?: number;
  timezone: string;
  question_paper?: PaperFile;
  markscheme?: PaperFile;
  analysis?: PaperAnalysis;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  paper_groups?: PaperGroup[];
  resource_files?: PaperFile[];
}
