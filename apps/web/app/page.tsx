import React from "react";
import Link from "next/link";
import {
  Activity,
  Users,
  Sparkles,
  FileText,
  Clock,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { SyntheticDisclaimer } from "@/components/shared/disclaimer";
import { getAllPatients } from "@/lib/fixtures/case-fixtures";

export default function Home() {
  const patients = getAllPatients();
  const heroPatient = patients.find((p) => p.id === "SYN-001") || patients[0];

  return (
    <div className="min-h-screen bg-background flex flex-col justify-between">
      {/* Top Header */}
      <header className="border-b border-border/80 bg-background/95 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5 font-bold tracking-tight text-foreground">
            <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
              <Activity className="h-4.5 w-4.5 text-white" />
            </div>
            <span className="text-base font-bold">CASETRACE</span>
          </div>

          <div className="flex items-center gap-3">
            <SyntheticDisclaimer compact />
          </div>
        </div>
      </header>

      {/* Main Hero & Workspace Portals */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex-1 flex flex-col justify-center">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 mb-4">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AI Clinical Investigation System</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-foreground">
            Reconstructing Medical Mysteries From Longitudinal Records
          </h1>
          <p className="mt-4 text-sm sm:text-base text-muted-foreground leading-relaxed">
            Investigating patient timelines across multiple encounters, connecting disparate
            clinical evidence, identifying contradictions, and verifying conclusions.
          </p>
        </div>

        {/* Workspaces Dual Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Hospital Workspace Card (My Responsibility) */}
          <div className="bg-card border-2 border-primary/30 rounded-2xl p-6 sm:p-8 shadow-md flex flex-col justify-between relative overflow-hidden group hover:border-primary transition-all">
            <div className="absolute top-0 right-0 bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-bl-lg">
              Active Workspace
            </div>

            <div>
              <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-5">
                <Users className="h-6 w-6" />
              </div>
              <h2 className="text-xl font-bold text-foreground">
                Hospital Information System
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-2 leading-relaxed">
                Browse synthetic patient charts, encounter histories, laboratory trends,
                written clinical reports, and diagnostic imaging studies.
              </p>

              {/* Quick Hero Case Shortcut */}
              {heroPatient && (
                <div className="mt-5 p-3 rounded-lg bg-secondary/60 border border-border text-xs">
                  <div className="flex items-center justify-between text-muted-foreground text-[11px] mb-1">
                    <span className="font-semibold text-primary">Hero Case (Timeline Mystery):</span>
                    <span className="font-mono">{heroPatient.case_id}</span>
                  </div>
                  <div className="font-bold text-foreground">
                    {heroPatient.display_name} ({heroPatient.id})
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {heroPatient.summary?.encounter_count} encounters •{" "}
                    {heroPatient.summary?.document_count} clinical reports
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-border flex items-center justify-between">
              <Link
                href="/patients"
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs sm:text-sm font-semibold hover:opacity-90 transition-opacity shadow-sm"
              >
                <span>Enter Hospital Workspace</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          {/* Investigation Workspace Card (Teammate's Responsibility) */}
          <div className="bg-card border border-border rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col justify-between hover:border-border/80 transition-all">
            <div>
              <div className="h-12 w-12 rounded-xl bg-secondary text-foreground flex items-center justify-center mb-5">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-xl font-bold text-foreground">
                Investigation Workspace
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-2 leading-relaxed">
                Multi-agent orchestration, contradiction discovery, timeline reconstruction,
                deterministic verification, and evidence-backed synthesis.
              </p>

              <div className="mt-5 space-y-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span>Real-time SSE Agent Activity Stream</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                  <span>Deterministic Fact & Date Verification</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                  <span>Traceable Evidence Citations</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border flex items-center justify-between">
              <Link
                href="/investigations"
                className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-secondary hover:bg-muted text-foreground text-xs sm:text-sm font-semibold transition-colors"
              >
                <span>Investigation Workspace</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/80 py-4 text-center text-xs text-muted-foreground">
        CASETRACE • AI Clinical Investigation Platform • Built for Codex Hackathon
      </footer>
    </div>
  );
}
