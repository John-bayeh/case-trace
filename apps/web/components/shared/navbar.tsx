"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Users, ShieldAlert, Sparkles } from "lucide-react";
import { SyntheticDisclaimer } from "./disclaimer";

export function HospitalNavbar() {
  const pathname = usePathname();

  const isPatientsActive = pathname.startsWith("/patients");
  const isInvestigationsActive = pathname.startsWith("/investigations");

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link
            href="/patients"
            className="flex items-center gap-2.5 font-bold tracking-tight text-foreground hover:opacity-90 transition-opacity"
          >
            <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center shadow-sm">
              <Activity className="h-4.5 w-4.5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold leading-tight">CASETRACE</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                Hospital Workspace
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
            <Link
              href="/patients"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                isPatientsActive
                  ? "bg-secondary text-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
              }`}
            >
              <Users className="h-4 w-4" />
              <span>Patients Directory</span>
            </Link>

            <Link
              href="/investigations"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                isInvestigationsActive
                  ? "bg-secondary text-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
              }`}
            >
              <Sparkles className="h-4 w-4 text-primary" />
              <span>Investigation Workspace</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium ml-1">
                AI Engine
              </span>
            </Link>
          </nav>
        </div>

        {/* Right disclaimer & actions */}
        <div className="flex items-center gap-3">
          <SyntheticDisclaimer compact />
        </div>
      </div>
    </header>
  );
}
