// Mirrors the backend response models in backend/app/schemas.py.

export interface Criterion {
  key?: string;
  label: string;
  weight: number;
  must_have: boolean;
}

export interface Job {
  id: string;
  title: string;
  department: string | null;
  location: string | null;
  description: string;
  criteria: Required<Criterion>[];
  status: "draft" | "open" | "closed";
  created_at: string;
  application_count: number;
  analysed_count: number;
  processing_count: number;
}

export type AppStatus =
  | "received" | "processing" | "analysed" | "failed"
  | "shortlisted" | "on_hold" | "not_progressing";

export type Decision = "shortlisted" | "on_hold" | "not_progressing";

export interface ApplicationSummary {
  id: string;
  job_id: string;
  candidate_name: string | null;
  candidate_email: string | null;
  status: AppStatus;
  failure_reason: string | null;
  cv_filename: string;
  created_at: string;
  overall_score: number | null;
  must_have_met: boolean | null;
  total_years_experience: number | null;
  top_skills: string[];
}

export interface CriterionResult {
  key: string;
  label: string;
  weight: number;
  must_have: boolean;
  score: number;
  assessed: boolean;
  evidence: string[];
  reasoning: string;
}

export interface ApplicationDetail {
  id: string;
  job: { id: string; title: string };
  candidate: { id: string; full_name: string | null; email: string | null; phone: string | null; location: string | null };
  status: AppStatus;
  failure_reason: string | null;
  cv_filename: string;
  created_at: string;
  profile: {
    summary: string | null;
    total_years_experience: number | null;
    skills: { name: string; category: string; years: number | null }[];
    experience: { title: string; company: string; start: string; end: string; highlights: string[] }[];
    education: { qualification: string; institution: string; year: string }[];
    certifications: string[];
    languages: string[];
    model_name: string;
    prompt_version: string;
  } | null;
  assessment: {
    overall_score: number;
    must_have_met: boolean;
    score_at_analysis: number;
    criteria: CriterionResult[];
    strengths: string[];
    gaps: string[];
    interview_questions: { question: string; purpose: string; criterion_key: string }[];
    model_name: string;
    prompt_version: string;
    created_at: string;
  } | null;
  reviews: { id: string; reviewer: string; decision: Decision; notes: string | null; created_at: string }[];
}

export interface UploadResult {
  batch_id: string;
  accepted: { application_id: string; filename: string }[];
  rejected: { filename: string; reason: string }[];
}
