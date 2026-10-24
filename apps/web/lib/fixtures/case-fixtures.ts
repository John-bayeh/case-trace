import fs from "fs";
import path from "path";
import {
  CaseData,
  ClinicalDocument,
  Encounter,
  ImagingStudy,
  Medication,
  Observation,
  PatientSummary,
} from "@/types/patient";

// In-memory cache for loaded cases
let cachedCases: CaseData[] | null = null;

function resolveCasesDirectory(): string {
  const candidates = [
    path.resolve(process.cwd(), "../../data/cases"),
    path.resolve(process.cwd(), "../data/cases"),
    path.resolve(process.cwd(), "data/cases"),
    path.resolve(process.cwd(), "../../cases"),
    "C:\\Users\\M  K  T\\OneDrive\\Documents\\Home\\esu vs\\Hackathon\\case-trace\\data\\cases",
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error("Unable to locate data/cases directory.");
}

/**
 * Load and return all canonical synthetic cases.
 */
export function getAllCases(): CaseData[] {
  if (cachedCases) {
    return cachedCases;
  }

  const casesDir = resolveCasesDirectory();
  const caseFolders = fs
    .readdirSync(casesDir)
    .filter((f) => f.startsWith("CASE-") && fs.statSync(path.join(casesDir, f)).isDirectory())
    .sort();

  const loaded: CaseData[] = [];

  for (const folder of caseFolders) {
    const caseJsonPath = path.join(casesDir, folder, "case.json");
    if (fs.existsSync(caseJsonPath)) {
      try {
        const raw = fs.readFileSync(caseJsonPath, "utf-8");
        const parsed = JSON.parse(raw) as CaseData;
        loaded.push(parsed);
      } catch (err) {
        console.error(`Failed to load case from ${caseJsonPath}:`, err);
      }
    }
  }

  cachedCases = loaded;
  return loaded;
}

/**
 * Find a case by synthetic patient ID (e.g. SYN-001) or case ID (e.g. CASE-001).
 */
export function getCaseByPatientId(patientId: string): CaseData | null {
  const cases = getAllCases();
  const match = cases.find(
    (c) =>
      c.patient?.id?.toLowerCase() === patientId.toLowerCase() ||
      c.patient?.synthetic_identifier?.toLowerCase() === patientId.toLowerCase() ||
      c.case_id?.toLowerCase() === patientId.toLowerCase()
  );
  return match || null;
}

/**
 * Return summary list of all available synthetic patients.
 */
export function getAllPatients(query?: string): PatientSummary[] {
  const cases = getAllCases();
  let list = cases.map((c) => {
    const encounters = c.encounters || [];
    const latestEncounter =
      encounters.length > 0
        ? [...encounters].sort(
            (a, b) =>
              new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
          )[0]
        : null;

    const summary = {
      encounter_count: encounters.length,
      document_count: (c.documents || []).length,
      observation_count: (c.observations || []).length,
      medication_count: (c.medications || []).length,
      imaging_study_count: (c.imaging_studies || []).length,
      latest_encounter_at: latestEncounter ? latestEncounter.started_at : null,
    };

    return {
      ...c.patient,
      case_id: c.case_id,
      summary,
      counts: summary,
      latest_encounter_at: summary.latest_encounter_at,
    } as PatientSummary;
  });

  if (query && query.trim()) {
    const q = query.trim().toLowerCase();
    list = list.filter(
      (p) =>
        p.id.toLowerCase().includes(q) ||
        p.synthetic_identifier.toLowerCase().includes(q) ||
        p.display_name.toLowerCase().includes(q) ||
        p.case_id.toLowerCase().includes(q)
    );
  }

  return list;
}

/**
 * Return detailed summary for a specific patient.
 */
export function getPatientSummary(patientId: string): PatientSummary | null {
  const c = getCaseByPatientId(patientId);
  if (!c) return null;

  const encounters = c.encounters || [];
  const latestEncounter =
    encounters.length > 0
      ? [...encounters].sort(
          (a, b) =>
            new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
        )[0]
      : null;

  const summary = {
    encounter_count: encounters.length,
    document_count: (c.documents || []).length,
    observation_count: (c.observations || []).length,
    medication_count: (c.medications || []).length,
    imaging_study_count: (c.imaging_studies || []).length,
    latest_encounter_at: latestEncounter ? latestEncounter.started_at : null,
  };

  return {
    ...c.patient,
    case_id: c.case_id,
    summary,
    counts: summary,
    latest_encounter_at: summary.latest_encounter_at,
  };
}

/**
 * Return encounters for a patient with optional filters.
 */
export function getEncounters(
  patientId: string,
  filters?: { department?: string; encounter_type?: string }
): Encounter[] {
  const c = getCaseByPatientId(patientId);
  if (!c) return [];

  let items = [...(c.encounters || [])];

  if (filters?.department) {
    items = items.filter(
      (e) => e.department.toLowerCase() === filters.department?.toLowerCase()
    );
  }

  if (filters?.encounter_type) {
    items = items.filter(
      (e) =>
        e.encounter_type.toLowerCase() === filters.encounter_type?.toLowerCase()
    );
  }

  // Sort descending by started_at
  return items.sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );
}

/**
 * Get single encounter by ID with associated documents and observations.
 */
export function getEncounterById(encounterId: string): Encounter | null {
  const cases = getAllCases();
  for (const c of cases) {
    const enc = (c.encounters || []).find((e) => e.id === encounterId);
    if (enc) {
      const documents = (c.documents || []).filter(
        (d) => d.encounter_id === encounterId
      );
      const observations = (c.observations || []).filter(
        (o) => o.encounter_id === encounterId
      );
      const medications = (c.medications || []).filter(
        (m) => m.encounter_id === encounterId
      );
      const clinical_events = (c.clinical_events || []).filter(
        (ev) => ev.encounter_id === encounterId
      );
      return {
        ...enc,
        documents,
        observations,
        medications,
        clinical_events,
      };
    }
  }
  return null;
}

/**
 * Return laboratory observations for a patient with optional filters.
 */
export function getObservations(
  patientId: string,
  filters?: { test?: string; status?: string }
): Observation[] {
  const c = getCaseByPatientId(patientId);
  if (!c) return [];

  let items = [...(c.observations || [])];

  if (filters?.test) {
    const q = filters.test.toLowerCase();
    items = items.filter(
      (o) =>
        (o.test_code && o.test_code.toLowerCase().includes(q)) ||
        (o.test_name && o.test_name.toLowerCase().includes(q))
    );
  }

  if (filters?.status) {
    items = items.filter(
      (o) => o.status.toLowerCase() === filters.status?.toLowerCase()
    );
  }

  // Sort chronologically descending by specimen_collected_at or reported_at
  return items.sort((a, b) => {
    const tA = new Date(a.specimen_collected_at || a.reported_at || 0).getTime();
    const tB = new Date(b.specimen_collected_at || b.reported_at || 0).getTime();
    return tB - tA;
  });
}

/**
 * Return medications for a patient.
 */
export function getMedications(patientId: string): Medication[] {
  const c = getCaseByPatientId(patientId);
  if (!c) return [];

  const items = [...(c.medications || [])];
  return items.sort((a, b) => {
    const tA = new Date(a.start_at || a.ordered_at || 0).getTime();
    const tB = new Date(b.start_at || b.ordered_at || 0).getTime();
    return tB - tA;
  });
}

/**
 * Return clinical documents for a patient with optional filters.
 */
export function getDocuments(
  patientId: string,
  filters?: { document_type?: string; search?: string }
): ClinicalDocument[] {
  const c = getCaseByPatientId(patientId);
  if (!c) return [];

  let items = [...(c.documents || [])];

  if (filters?.document_type) {
    items = items.filter(
      (d) =>
        d.document_type.toLowerCase() === filters.document_type?.toLowerCase()
    );
  }

  if (filters?.search) {
    const q = filters.search.toLowerCase();
    items = items.filter(
      (d) =>
        d.title.toLowerCase().includes(q) ||
        d.id.toLowerCase().includes(q) ||
        d.author.toLowerCase().includes(q) ||
        (d.text_content && d.text_content.toLowerCase().includes(q))
    );
  }

  // Sort descending by event_at or authored_at
  return items.sort((a, b) => {
    const tA = new Date(a.event_at || a.authored_at).getTime();
    const tB = new Date(b.event_at || b.authored_at).getTime();
    return tB - tA;
  });
}

/**
 * Get single clinical document by ID across all cases.
 */
export function getDocumentById(documentId: string): ClinicalDocument | null {
  const cases = getAllCases();
  for (const c of cases) {
    const doc = (c.documents || []).find(
      (d) => d.id.toLowerCase() === documentId.toLowerCase()
    );
    if (doc) return doc;
  }
  return null;
}

/**
 * Return imaging studies for a patient.
 */
export function getImaging(patientId: string): ImagingStudy[] {
  const c = getCaseByPatientId(patientId);
  if (!c) return [];

  const items = [...(c.imaging_studies || [])];
  return items.sort((a, b) => {
    const tA = new Date(a.performed_at || a.reported_at || 0).getTime();
    const tB = new Date(b.performed_at || b.reported_at || 0).getTime();
    return tB - tA;
  });
}
