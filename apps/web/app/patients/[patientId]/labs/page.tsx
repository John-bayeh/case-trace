import React from "react";
import { notFound } from "next/navigation";
import { getObservations, getCaseByPatientId } from "@/lib/fixtures/case-fixtures";
import { LabsTable } from "@/components/labs/labs-table";

export const metadata = {
  title: "Labs & Observations | Patient Chart | CASETRACE",
};

export default async function LabsPage(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const caseData = getCaseByPatientId(patientId);

  if (!caseData) {
    notFound();
  }

  const observations = getObservations(patientId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground">
            Laboratory Results & Observations
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Objective longitudinal measurements, laboratory tests, reference ranges, and flags
          </p>
        </div>
      </div>

      <LabsTable observations={observations} />
    </div>
  );
}
