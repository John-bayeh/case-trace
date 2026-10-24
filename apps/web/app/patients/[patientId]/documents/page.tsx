import React from "react";
import { notFound } from "next/navigation";
import { getDocuments, getCaseByPatientId } from "@/lib/fixtures/case-fixtures";
import { DocumentList } from "@/components/documents/document-list";

export const metadata = {
  title: "Clinical Documents & Reports | Patient Chart | CASETRACE",
};

export default async function DocumentsPage(props: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await props.params;
  const caseData = getCaseByPatientId(patientId);

  if (!caseData) {
    notFound();
  }

  const documents = getDocuments(patientId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground">
            Clinical Documents & Written Reports
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Full structured clinical notes, assessments, radiology reports, and documentation provenance
          </p>
        </div>
      </div>

      <DocumentList documents={documents} />
    </div>
  );
}
