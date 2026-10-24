import React from "react";
import { notFound } from "next/navigation";
import { getMedications, getCaseByPatientId } from "@/lib/fixtures/case-fixtures";
import { MedicationsTable } from "@/components/medications/medications-table";

export const metadata = {
  title: "Medications | Patient Chart | CASETRACE",
};

export default async function MedicationsPage(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const caseData = getCaseByPatientId(patientId);

  if (!caseData) {
    notFound();
  }

  const medications = getMedications(patientId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground">
            Medication History & Prescriptions
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Active regimens, historical treatments, dosages, and prescribing clinicians
          </p>
        </div>
      </div>

      <MedicationsTable medications={medications} />
    </div>
  );
}
