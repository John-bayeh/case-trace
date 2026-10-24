import React from "react";
import { getAllPatients } from "@/lib/fixtures/case-fixtures";
import { HospitalNavbar } from "@/components/shared/navbar";
import { SyntheticDisclaimer } from "@/components/shared/disclaimer";
import { PatientTable } from "@/components/patients/patient-table";
import { Users, FileSpreadsheet } from "lucide-react";

export const metadata = {
  title: "Patient Directory | CASETRACE Hospital Workspace",
  description: "Browse synthetic clinical records for AI medical investigation",
};

export default function PatientsPage() {
  const patients = getAllPatients();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <HospitalNavbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Synthetic Disclaimer */}
        <SyntheticDisclaimer />

        {/* Directory Title & Overview */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                <Users className="h-4.5 w-4.5" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Synthetic Patient Directory
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Select a synthetic patient record to inspect encounters, clinical notes, laboratory
              observations, and trigger AI investigation workflows.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground border border-border">
              {patients.length} Synthetic Cases Loaded
            </span>
          </div>
        </div>

        {/* Patient Table Component */}
        <PatientTable patients={patients} />
      </main>

      <footer className="border-t border-border/80 py-4 text-center text-xs text-muted-foreground">
        CASETRACE • Clinical Evidence Investigation Engine • All data synthetic
      </footer>
    </div>
  );
}
