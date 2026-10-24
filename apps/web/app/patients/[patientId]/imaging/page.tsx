import React from "react";
import { notFound } from "next/navigation";
import { getImaging, getCaseByPatientId } from "@/lib/fixtures/case-fixtures";
import { ImagingList } from "@/components/imaging/imaging-list";

export const metadata = {
  title: "Imaging Studies | Patient Chart | CASETRACE",
};

export default async function ImagingPage(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const caseData = getCaseByPatientId(patientId);

  if (!caseData) {
    notFound();
  }

  const imaging = getImaging(patientId);

  return (
    <div className="space-y-4">
      <ImagingList imaging={imaging} />
    </div>
  );
}
