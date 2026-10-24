import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPatientSummary } from "@/lib/fixtures/case-fixtures";
import { HospitalNavbar } from "@/components/shared/navbar";
import { SyntheticDisclaimer } from "@/components/shared/disclaimer";
import { PatientHeader } from "@/components/patients/patient-header";
import { ChartNav } from "@/components/patients/chart-nav";
import { AlertCircle, ArrowLeft } from "lucide-react";

export async function generateMetadata(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const patient = getPatientSummary(patientId);
  if (!patient) return { title: "Patient Not Found | CASETRACE" };
  return {
    title: `${patient.display_name} (${patient.id}) | Patient Chart | CASETRACE`,
    description: `Synthetic medical record chart for ${patient.display_name}`,
  };
}

export default async function PatientChartLayout(props: {
  children: React.ReactNode;
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const patient = getPatientSummary(patientId);

  if (!patient) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <HospitalNavbar />
        <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-16 text-center">
          <div className="p-8 bg-card border border-border rounded-xl shadow-sm">
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-3" />
            <h1 className="text-xl font-bold text-foreground">
              Patient Record Not Found
            </h1>
            <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
              No synthetic patient record matches identifier{" "}
              <code className="font-mono font-bold text-foreground">{patientId}</code>.
            </p>
            <div className="mt-6">
              <Link
                href="/patients"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Return to Patient Directory</span>
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <HospitalNavbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Synthetic Disclaimer */}
        <SyntheticDisclaimer className="mb-4" />

        {/* Patient Identity Header */}
        <PatientHeader patient={patient} />

        {/* Persistent Chart Section Tabs */}
        <ChartNav patientId={patient.id} />

        {/* Tab Page Contents */}
        <div>{props.children}</div>
      </main>

      <footer className="border-t border-border/80 py-4 text-center text-xs text-muted-foreground">
        CASETRACE Hospital Information System • Synthetic Demo Records Only
      </footer>
    </div>
  );
}
