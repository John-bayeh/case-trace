import { NextRequest, NextResponse } from "next/server";
import { getPatientSummary } from "@/lib/fixtures/case-fixtures";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  try {
    const { patientId } = await context.params;
    const patient = getPatientSummary(patientId);

    if (!patient) {
      return NextResponse.json(
        {
          error: {
            code: "PATIENT_NOT_FOUND",
            message: `Patient ${patientId} was not found.`,
          },
          meta: { request_id: `req-${Date.now()}` },
        },
        { status: 404 }
      );
    }

    return NextResponse.json({
      data: patient,
      ...patient,
      meta: { request_id: `req-${Date.now()}` },
    });
  } catch (error) {
    console.error("GET /api/hospital/v1/patients/[patientId] error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch patient" },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
