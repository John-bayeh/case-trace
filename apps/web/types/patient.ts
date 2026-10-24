/**
 * TypeScript models for CASETRACE Hospital Workspace and Clinical Records.
 * Conforms to docs/frontend-backend-contract.md, docs/hospital-api.md, and docs/case-schema.md.
 */

export type ISODateString = string;

export interface Patient {
  id: string;
  case_id: string;
  synthetic_identifier: string;
  display_name: string;
  date_of_birth: string;
  sex: "male" | "female" | "other" | "unknown" | string;
  created_at?: ISODateString;
}

export interface PatientCounts {
  encounter_count: number;
  document_count: number;
  observation_count: number;
  medication_count: number;
  imaging_study_count: number;
  latest_encounter_at?: ISODateString | null;
}

export interface PatientSummary extends Patient {
  summary?: PatientCounts;
  counts?: PatientCounts;
  latest_encounter_at?: ISODateString | null;
}

export interface PatientListResponse {
  items?: PatientSummary[];
  data?: PatientSummary[];
  total: number;
}

export interface Encounter {
  id: string;
  patient_id: string;
  encounter_type: string;
  department: string;
  provider_name: string;
  started_at: ISODateString;
  ended_at: ISODateString | null;
  status: string;
  // Optional convenience references
  clinical_events?: ClinicalEvent[];
  documents?: ClinicalDocument[];
  observations?: Observation[];
  medications?: Medication[];
}

export interface EncounterListResponse {
  items?: Encounter[];
  data?: Encounter[];
  total: number;
}

export interface ClinicalEvent {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  event_type: string;
  occurred_at: ISODateString | null;
  documented_at: ISODateString | null;
  description: string;
  source_document_id: string | null;
}

export interface Observation {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  test_code: string | null;
  test_name: string;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  reference_range_low: number | null;
  reference_range_high: number | null;
  reference_low?: number | null;
  reference_high?: number | null;
  status: string;
  specimen_collected_at: ISODateString | null;
  reported_at: ISODateString | null;
  source_document_id: string | null;
}

export interface ObservationListResponse {
  items?: Observation[];
  data?: Observation[];
  total: number;
}

export interface Medication {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  medication_name: string;
  generic_name: string;
  dose: number | string | null;
  dose_unit: string | null;
  route: string | null;
  frequency: string | null;
  start_at: string | null;
  end_at: string | null;
  status: "active" | "completed" | "discontinued" | string;
  prescriber: string | null;
  ordered_at: ISODateString | null;
  source_document_id: string | null;
}

export interface MedicationListResponse {
  items?: Medication[];
  data?: Medication[];
  total: number;
}

export interface DocumentMetadata {
  department?: string;
  synthetic_label?: string;
  author_role?: string;
  [key: string]: unknown;
}

export interface DocumentAsset {
  id: string;
  mime_type: string;
  url: string;
}

export interface ClinicalDocument {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  document_type: string;
  title: string;
  author: string;
  event_at: ISODateString;
  authored_at: ISODateString;
  mime_type: string;
  storage_path?: string;
  text_content?: string | null;
  metadata?: DocumentMetadata | null;
  asset?: DocumentAsset | null;
}

export interface DocumentListResponse {
  items?: ClinicalDocument[];
  data?: ClinicalDocument[];
  total: number;
}

export interface ImagingStudy {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  modality: string;
  body_region: string;
  performed_at: ISODateString | null;
  reported_at: ISODateString | null;
  status: string;
  report_document_id: string | null;
  asset?: DocumentAsset | null;
}

export interface ImagingListResponse {
  items?: ImagingStudy[];
  data?: ImagingStudy[];
  total: number;
}

export interface Diagnosis {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  name: string;
  code_system: string | null;
  code: string | null;
  status: string;
  diagnosed_at: ISODateString | null;
}

export interface Symptom {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  name: string;
  onset_at: string | null;
  severity: string | null;
  frequency: string | null;
  status: string;
  description: string | null;
}

export interface CaseData {
  case_id: string;
  version: string;
  status: string;
  created_at: string;
  updated_at: string;
  patient: Patient;
  encounters: Encounter[];
  clinical_events: ClinicalEvent[];
  observations: Observation[];
  medications: Medication[];
  documents: ClinicalDocument[];
  imaging_studies: ImagingStudy[];
  diagnoses?: Diagnosis[];
  symptoms?: Symptom[];
}
