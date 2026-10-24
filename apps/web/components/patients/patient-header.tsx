"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  User,
  Calendar,
  Sparkles,
  FileText,
  FlaskConical,
  Clock,
  ArrowLeft,
  Pill,
} from "lucide-react";
import { PatientSummary } from "@/types/patient";
import { calculateAge, formatDate } from "@/lib/utils";
import { InvestigateModal } from "./investigate-modal";

interface PatientHeaderProps {
  patient: PatientSummary;
}

export function PatientHeader({ patient }: PatientHeaderProps) {
  const [showInvestigateModal, setShowInvestigateModal] = useState(false);

  const counts = patient.summary || patient.counts || {
    encounter_count: 0,
    document_count: 0,
    observation_count: 0,
    medication_count: 0,
  };

  return (
    <>
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden mb-6">
        {/* Top bar with back link & actions */}
        <div className="px-6 py-3 border-b border-border/80 bg-muted/30 flex items-center justify-between">
          <Link
            href="/patients"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Patient Directory</span>
          </Link>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/60">
              {patient.case_id}
            </span>
            <button
              onClick={() => setShowInvestigateModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity shadow-sm"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Investigate Patient</span>
            </button>
          </div>
        </div>

        {/* Main Identity Information */}
        <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="h-14 w-14 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20">
              <User className="h-7 w-7" />
            </div>

            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
                  {patient.display_name}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-secondary text-secondary-foreground border border-border">
                  {patient.id}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono text-muted-foreground bg-muted/60">
                  MRN: {patient.synthetic_identifier}
                </span>
              </div>

              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground flex-wrap">
                <div className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>
                    DOB: <strong>{formatDate(patient.date_of_birth)}</strong> (
                    {calculateAge(patient.date_of_birth)})
                  </span>
                </div>
                <span className="text-border">•</span>
                <div>
                  Sex:{" "}
                  <strong className="capitalize">{patient.sex || "Unknown"}</strong>
                </div>
                <span className="text-border">•</span>
                <div>
                  Synthetic Status:{" "}
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                    Verified Synthetic Fixture
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Record Counts */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-2.5 rounded-lg bg-secondary/50 border border-border/60 text-center min-w-[80px]">
              <div className="flex items-center justify-center text-muted-foreground mb-1">
                <Clock className="h-3.5 w-3.5" />
              </div>
              <div className="text-base font-bold text-foreground">
                {counts.encounter_count}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase font-medium">
                Encounters
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-secondary/50 border border-border/60 text-center min-w-[80px]">
              <div className="flex items-center justify-center text-muted-foreground mb-1">
                <FileText className="h-3.5 w-3.5" />
              </div>
              <div className="text-base font-bold text-foreground">
                {counts.document_count}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase font-medium">
                Reports
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-secondary/50 border border-border/60 text-center min-w-[80px]">
              <div className="flex items-center justify-center text-muted-foreground mb-1">
                <FlaskConical className="h-3.5 w-3.5" />
              </div>
              <div className="text-base font-bold text-foreground">
                {counts.observation_count}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase font-medium">
                Lab Tests
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-secondary/50 border border-border/60 text-center min-w-[80px]">
              <div className="flex items-center justify-center text-muted-foreground mb-1">
                <Pill className="h-3.5 w-3.5" />
              </div>
              <div className="text-base font-bold text-foreground">
                {counts.medication_count}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase font-medium">
                Medications
              </div>
            </div>
          </div>
        </div>
      </div>

      <InvestigateModal
        isOpen={showInvestigateModal}
        onClose={() => setShowInvestigateModal(false)}
        patientId={patient.id}
        patientName={patient.display_name}
        caseId={patient.case_id}
      />
    </>
  );
}
