import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getCaseByPatientId,
  getEncounters,
  getObservations,
  getDocuments,
  getMedications,
} from "@/lib/fixtures/case-fixtures";
import { formatDate, formatDateTime, calculateAge } from "@/lib/utils";
import {
  Clock,
  FlaskConical,
  FileText,
  Pill,
  ChevronRight,
  AlertTriangle,
  Activity,
  HeartPulse,
} from "lucide-react";

export default async function PatientOverviewPage(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const caseData = getCaseByPatientId(patientId);

  if (!caseData) {
    notFound();
  }

  const patient = caseData.patient;
  const encounters = getEncounters(patientId).slice(0, 3);
  const observations = getObservations(patientId).slice(0, 6);
  const documents = getDocuments(patientId).slice(0, 4);
  const medications = getMedications(patientId).slice(0, 4);
  const diagnoses = caseData.diagnoses || [];
  const symptoms = caseData.symptoms || [];

  return (
    <div className="space-y-6">
      {/* Top Banner Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Patient Demographics & Baseline */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Demographic Profile
            </h3>
            <span className="text-[11px] font-mono text-muted-foreground">
              {caseData.case_id}
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1 border-b border-border/40">
              <span className="text-muted-foreground">Legal Name:</span>
              <span className="font-semibold text-foreground">{patient.display_name}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/40">
              <span className="text-muted-foreground">Medical Record Number:</span>
              <span className="font-mono font-medium text-foreground">
                {patient.synthetic_identifier}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/40">
              <span className="text-muted-foreground">Date of Birth:</span>
              <span className="font-mono text-foreground">
                {formatDate(patient.date_of_birth)} ({calculateAge(patient.date_of_birth)})
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/40">
              <span className="text-muted-foreground">Biological Sex:</span>
              <span className="capitalize font-medium text-foreground">
                {patient.sex || "Unknown"}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Record Version:</span>
              <span className="font-mono text-foreground">v{caseData.version}</span>
            </div>
          </div>
        </div>

        {/* Documented Diagnoses & Active Problems */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Documented Diagnoses
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-foreground font-semibold">
              {diagnoses.length} Registered
            </span>
          </div>

          {diagnoses.length === 0 ? (
            <p className="text-xs text-muted-foreground italic py-4">
              No formal ICD/coded diagnoses entered in initial registry.
            </p>
          ) : (
            <div className="space-y-2">
              {diagnoses.map((dx) => (
                <div
                  key={dx.id}
                  className="p-2.5 rounded-lg bg-secondary/40 border border-border/60 text-xs"
                >
                  <div className="flex justify-between items-start">
                    <span className="font-semibold text-foreground">{dx.name}</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-muted text-muted-foreground capitalize">
                      {dx.status}
                    </span>
                  </div>
                  {dx.code && (
                    <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
                      Code: {dx.code} ({dx.code_system || "ICD"})
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Clinical Symptoms */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Reported Symptoms
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-foreground font-semibold">
              {symptoms.length}
            </span>
          </div>

          {symptoms.length === 0 ? (
            <p className="text-xs text-muted-foreground italic py-4">
              Symptoms captured inline within clinical encounter notes.
            </p>
          ) : (
            <div className="space-y-2">
              {symptoms.map((sym) => (
                <div
                  key={sym.id}
                  className="p-2.5 rounded-lg bg-secondary/40 border border-border/60 text-xs"
                >
                  <div className="flex justify-between items-start">
                    <span className="font-semibold text-foreground">{sym.name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      Onset: {sym.onset_at || "—"}
                    </span>
                  </div>
                  {sym.description && (
                    <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
                      {sym.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Two Column Detailed Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Encounters */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-bold text-foreground">Recent Encounters</h3>
            </div>
            <Link
              href={`/patients/${patientId}/encounters`}
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-0.5"
            >
              <span>View All Encounters</span>
              <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {encounters.map((enc) => (
              <div
                key={enc.id}
                className="p-3 rounded-lg border border-border/80 bg-muted/20 flex items-center justify-between gap-3 text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-foreground">{enc.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-primary/10 text-primary">
                      {enc.encounter_type}
                    </span>
                  </div>
                  <div className="text-muted-foreground mt-1">
                    {enc.department} • {enc.provider_name}
                  </div>
                </div>
                <div className="text-right shrink-0 font-mono text-[11px] text-muted-foreground">
                  {formatDateTime(enc.started_at)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Clinical Reports & Documents */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-bold text-foreground">Recent Clinical Reports</h3>
            </div>
            <Link
              href={`/patients/${patientId}/documents`}
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-0.5"
            >
              <span>View All Reports ({caseData.documents.length})</span>
              <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="p-3 rounded-lg border border-border/80 bg-muted/20 flex items-center justify-between gap-3 text-xs"
              >
                <div>
                  <div className="font-semibold text-foreground">{doc.title}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {doc.id}
                    </span>
                    <span className="text-border">•</span>
                    <span className="text-[11px] text-muted-foreground capitalize">
                      {doc.document_type.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
                <div className="text-right shrink-0 font-mono text-[11px] text-muted-foreground">
                  {formatDate(doc.event_at)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Key Laboratory Observations */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-bold text-foreground">Laboratory Tests</h3>
            </div>
            <Link
              href={`/patients/${patientId}/labs`}
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-0.5"
            >
              <span>View Full Lab Record</span>
              <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-border/60">
            {observations.map((obs) => {
              const low = obs.reference_range_low ?? obs.reference_low;
              const high = obs.reference_range_high ?? obs.reference_high;
              const isAbnormal =
                obs.value_numeric !== null &&
                ((low !== null && low !== undefined && obs.value_numeric < low) ||
                  (high !== null && high !== undefined && obs.value_numeric > high));

              return (
                <div key={obs.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-foreground">{obs.test_name}</div>
                    <div className="text-[11px] font-mono text-muted-foreground">
                      {formatDate(obs.specimen_collected_at || obs.reported_at)}
                    </div>
                  </div>
                  <div className="text-right font-mono">
                    <span
                      className={`font-bold ${
                        isAbnormal ? "text-rose-600 dark:text-rose-400" : "text-foreground"
                      }`}
                    >
                      {obs.value_numeric !== null ? obs.value_numeric : obs.value_text} {obs.unit || ""}
                    </span>
                    {isAbnormal && (
                      <span className="ml-2 px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                        FLAG
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Current Medications */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="flex items-center gap-2">
              <Pill className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-bold text-foreground">Medications</h3>
            </div>
            <Link
              href={`/patients/${patientId}/medications`}
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-0.5"
            >
              <span>View Full Medication History</span>
              <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {medications.map((med) => (
              <div
                key={med.id}
                className="p-3 rounded-lg border border-border/80 bg-muted/20 flex items-center justify-between gap-3 text-xs"
              >
                <div>
                  <div className="font-semibold text-foreground">
                    {med.medication_name} ({med.dose} {med.dose_unit || ""})
                  </div>
                  <div className="text-muted-foreground text-[11px] capitalize mt-0.5">
                    {med.generic_name} • {med.frequency ? med.frequency.replace(/_/g, " ") : "As directed"}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                      med.status === "active"
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "bg-secondary text-secondary-foreground"
                    }`}
                  >
                    {med.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
