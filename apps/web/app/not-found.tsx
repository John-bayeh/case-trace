import React from "react";
import Link from "next/link";
import { ArrowLeft, FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-md w-full p-8 bg-card border border-border rounded-xl shadow-sm">
        <FileQuestion className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
        <h1 className="text-xl font-bold text-foreground">404 - Page Not Found</h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-2">
          The requested clinical record or workspace page does not exist.
        </p>
        <div className="mt-6">
          <Link
            href="/patients"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Patients</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
