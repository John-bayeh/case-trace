/**
 * Centralized API Client for CASETRACE Hospital Workspace.
 * All patient and clinical record requests must go through this module.
 */

import {
  ClinicalDocument,
  DocumentListResponse,
  Encounter,
  EncounterListResponse,
  ImagingListResponse,
  ImagingStudy,
  Medication,
  MedicationListResponse,
  Observation,
  ObservationListResponse,
  PatientListResponse,
  PatientSummary,
} from "@/types/patient";

const getApiBase = (): string => {
  // If NEXT_PUBLIC_API_URL is set and starts with http, use it
  if (
    typeof process.env.NEXT_PUBLIC_API_URL === "string" &&
    process.env.NEXT_PUBLIC_API_URL.trim() !== ""
  ) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  // Otherwise default to local relative API
  return "";
};

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const base = getApiBase();
  const url = `${base}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let errorMessage = `HTTP error ${res.status}: ${res.statusText}`;
    try {
      const errBody = await res.json();
      if (errBody?.error?.message) {
        errorMessage = errBody.error.message;
      }
    } catch {
      // Ignore JSON parse errors on failure
    }
    throw new Error(errorMessage);
  }

  return (await res.json()) as T;
}

export const patientsApi = {
  /**
   * List available synthetic patients with optional search query.
   */
  async listPatients(query?: string): Promise<PatientSummary[]> {
    const q = query ? `?query=${encodeURIComponent(query)}` : "";
    const res = await fetchJson<PatientListResponse>(`/api/hospital/v1/patients${q}`);
    return res.data || res.items || [];
  },

  /**
   * Get single patient summary by ID or MRN.
   */
  async getPatient(patientId: string): Promise<PatientSummary> {
    const res = await fetchJson<{ data?: PatientSummary } & PatientSummary>(
      `/api/hospital/v1/patients/${encodeURIComponent(patientId)}`
    );
    return res.data || res;
  },

  /**
   * Get encounters for a patient with optional filters.
   */
  async getEncounters(
    patientId: string,
    filters?: { department?: string; encounter_type?: string }
  ): Promise<Encounter[]> {
    const params = new URLSearchParams();
    if (filters?.department) params.set("department", filters.department);
    if (filters?.encounter_type) params.set("encounter_type", filters.encounter_type);
    const qs = params.toString() ? `?${params.toString()}` : "";

    const res = await fetchJson<EncounterListResponse>(
      `/api/hospital/v1/patients/${encodeURIComponent(patientId)}/encounters${qs}`
    );
    return res.data || res.items || [];
  },

  /**
   * Get laboratory observations for a patient with optional filters.
   */
  async getObservations(
    patientId: string,
    filters?: { test?: string; status?: string }
  ): Promise<Observation[]> {
    const params = new URLSearchParams();
    if (filters?.test) params.set("test", filters.test);
    if (filters?.status) params.set("status", filters.status);
    const qs = params.toString() ? `?${params.toString()}` : "";

    const res = await fetchJson<ObservationListResponse>(
      `/api/hospital/v1/patients/${encodeURIComponent(patientId)}/observations${qs}`
    );
    return res.data || res.items || [];
  },

  /**
   * Get medications for a patient.
   */
  async getMedications(patientId: string): Promise<Medication[]> {
    const res = await fetchJson<MedicationListResponse>(
      `/api/hospital/v1/patients/${encodeURIComponent(patientId)}/medications`
    );
    return res.data || res.items || [];
  },

  /**
   * Get clinical documents/reports for a patient with optional filters.
   */
  async getDocuments(
    patientId: string,
    filters?: { document_type?: string; search?: string }
  ): Promise<ClinicalDocument[]> {
    const params = new URLSearchParams();
    if (filters?.document_type) params.set("document_type", filters.document_type);
    if (filters?.search) params.set("search", filters.search);
    const qs = params.toString() ? `?${params.toString()}` : "";

    const res = await fetchJson<DocumentListResponse>(
      `/api/hospital/v1/patients/${encodeURIComponent(patientId)}/documents${qs}`
    );
    return res.data || res.items || [];
  },

  /**
   * Get single clinical document by ID.
   */
  async getDocument(documentId: string): Promise<ClinicalDocument> {
    const res = await fetchJson<{ data?: ClinicalDocument } & ClinicalDocument>(
      `/api/hospital/v1/documents/${encodeURIComponent(documentId)}`
    );
    return res.data || res;
  },

  /**
   * Get imaging studies for a patient.
   */
  async getImaging(patientId: string): Promise<ImagingStudy[]> {
    const res = await fetchJson<ImagingListResponse>(
      `/api/hospital/v1/patients/${encodeURIComponent(patientId)}/imaging`
    );
    return res.data || res.items || [];
  },
};
