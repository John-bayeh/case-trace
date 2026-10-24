import React from "react";
import { AlertTriangle } from "lucide-react";

interface DisclaimerProps {
  compact?: boolean;
  className?: string;
}

export function SyntheticDisclaimer({ compact = false, className = "" }: DisclaimerProps) {
  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30 ${className}`}
        role="alert"
      >
        <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
        <span>SYNTHETIC DEMO — NOT FOR CLINICAL USE</span>
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border border-amber-500/30 bg-amber-50/80 dark:bg-amber-950/20 px-4 py-2.5 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between gap-3 shadow-sm ${className}`}
      role="alert"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
        <span className="font-semibold tracking-wide">
          DEMONSTRATION ONLY — SYNTHETIC PATIENT RECORD — NOT FOR CLINICAL USE
        </span>
      </div>
      <span className="text-[11px] text-amber-700/80 dark:text-amber-400/70 hidden sm:inline">
        All patients, notes, timestamps, and laboratory values are simulated fixtures.
      </span>
    </div>
  );
}
