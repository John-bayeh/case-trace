"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  X,
  FileSearch,
  Clock,
  FlaskConical,
  Pill,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
} from "lucide-react";

interface InvestigateModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  patientName: string;
  caseId: string;
}

export function InvestigateModal({
  isOpen,
  onClose,
  patientId,
  patientName,
  caseId,
}: InvestigateModalProps) {
  const router = useRouter();
  const [objective, setObjective] = useState<string>("timeline_investigation");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const objectives = [
    {
      id: "timeline_investigation",
      title: "Timeline Reconstruction & Contradictions",
      description:
        "Connect records across time to surface chronological inconsistencies between notes, labs, and encounters (Hero Case).",
      icon: Clock,
      recommended: true,
    },
    {
      id: "full_record_investigation",
      title: "Comprehensive Clinical Investigation",
      description:
        "Multi-agent review across all documents, encounters, lab tests, and medications for synthetic patient records.",
      icon: FileSearch,
    },
    {
      id: "laboratory_investigation",
      title: "Laboratory & Biomarker Analysis",
      description:
        "Track chronological lab trends, abnormal flags, and missing tests against documented clinical notes.",
      icon: FlaskConical,
    },
    {
      id: "medication_investigation",
      title: "Medication Chronology & Regimen Review",
      description:
        "Reconstruct active vs historical prescriptions and identify undocumented medication changes.",
      icon: Pill,
    },
  ];

  const handleLaunch = async () => {
    setIsSubmitting(true);
    setStatusMessage("Preparing investigation session...");

    try {
      // Check if backend investigations endpoint responds, or route to investigation workspace
      const res = await fetch("/api/investigations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: patientId,
          objective,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const investigationId = data.investigation_id || data.id || "INV-001";
        router.push(`/investigations/${investigationId}`);
        onClose();
        return;
      }
    } catch {
      // If backend API is not yet running or returns 404, provide clean handoff to teammate's workspace
    }

    // Fallback: Integration-ready handoff redirect to teammate's investigation route
    setStatusMessage(
      `Handoff payload prepared for ${patientId} (${caseId}). Forwarding to Investigation Workspace...`
    );
    setTimeout(() => {
      setIsSubmitting(false);
      router.push(`/investigations?patient_id=${encodeURIComponent(patientId)}&objective=${encodeURIComponent(objective)}`);
      onClose();
    }, 900);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="investigate-title"
    >
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-lg w-full overflow-hidden text-card-foreground">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/30">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 id="investigate-title" className="text-base font-bold leading-tight">
                Initiate AI Investigation
              </h2>
              <p className="text-xs text-muted-foreground">
                Handoff patient record to CASETRACE Multi-Agent Engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1.5 rounded-md hover:bg-secondary transition-colors"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Patient Context Tag */}
          <div className="bg-secondary/60 rounded-lg p-3 text-xs flex items-center justify-between border border-border/60">
            <div>
              <span className="text-muted-foreground">Subject: </span>
              <span className="font-semibold">{patientName}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-mono font-medium">
                {patientId}
              </span>
              <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                {caseId}
              </span>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground uppercase tracking-wider block mb-2">
              Select Investigation Objective
            </label>
            <div className="space-y-2">
              {objectives.map((obj) => {
                const Icon = obj.icon;
                const isSelected = objective === obj.id;
                return (
                  <button
                    key={obj.id}
                    type="button"
                    onClick={() => setObjective(obj.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all flex items-start gap-3 ${
                      isSelected
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : "border-border hover:bg-muted/40"
                    }`}
                  >
                    <div
                      className={`h-7 w-7 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-foreground">
                          {obj.title}
                        </span>
                        {obj.recommended && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 font-medium border border-amber-500/20">
                            Hero Target
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                        {obj.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Integration Status Notice */}
          <div className="rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/40 p-3 text-[11px] text-blue-800 dark:text-blue-300 flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
            <p>
              <strong>Investigation Handoff Ready:</strong> Passes patient{" "}
              <code>{patientId}</code> with structured clinical context. Will connect with
              the Investigation Workspace SSE event stream.
            </p>
          </div>

          {statusMessage && (
            <p className="text-xs text-muted-foreground italic text-center animate-pulse">
              {statusMessage}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-border bg-muted/20 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleLaunch}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            <span>{isSubmitting ? "Initiating..." : "Start Investigation"}</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
