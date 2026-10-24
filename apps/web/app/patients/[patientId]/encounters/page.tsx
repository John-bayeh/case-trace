import React from "react";
import { notFound } from "next/navigation";
import { getEncounters, getCaseByPatientId } from "@/lib/fixtures/case-fixtures";
import { EncounterList } from "@/components/encounters/encounter-list";

export const metadata = {
  title: "Encounters | Patient Chart | CASETRACE",
};

export default async function EncountersPage(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const caseData = getCaseByPatientId(patientId);

  if (!caseData) {
    notFound();
  }

  const encounters = getEncounters(patientId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground">Encounter History</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Chronological log of outpatient, specialist, and urgent care encounters
          </p>
        </div>
      </div>

      <EncounterList encounters={encounters} />
    </div>
  );
}
