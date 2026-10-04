export type DocumentSlot = 'id' | 'marksheet' | 'income';

export type ExtractedField = {
  value: string | null;
  confidence: number;
  source: string;
};

export type DocumentRecord = {
  id: number;
  slot: DocumentSlot;
  filename: string;
  detected_type: string | null;
  confidence: number | null;
  extracted_fields: Record<string, ExtractedField>;
  status: string;
  rejection_reason: string | null;
};

export type CheckRecord = {
  key: string;
  label: string;
  status: string;
  detail: string;
};

export type IssueRecord = {
  severity: string;
  code: string;
  message: string;
  suggestion: string;
  source: string | null;
};

export type Application = {
  id: number;
  name: string;
  email: string;
  date_of_birth: string;
  application_type: string;
  marks_percentage: string;
  family_income: string;
  status: string;
  health: number;
  created_at: string;
  updated_at: string;
  documents: DocumentRecord[];
  checks: CheckRecord[];
  issues: IssueRecord[];
};

export type AdminRow = {
  id: number;
  name: string;
  application_type: string;
  status: string;
  health: number;
  document_count: number;
  updated_at: string;
};

export type ApplicationForm = {
  name: string;
  email: string;
  date_of_birth: string;
  application_type: 'Scholarship' | 'Admission' | 'Loan';
  marks_percentage: string;
  family_income: string;
};
