import { NextRequest, NextResponse } from "next/server";
import { getObservations } from "@/lib/fixtures/case-fixtures";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  try {
    const { patientId } = await context.params;
    const searchParams = request.nextUrl.searchParams;
    const test = searchParams.get("test") || undefined;
    const status = searchParams.get("status") || undefined;

    const items = getObservations(patientId, { test, status });

    return NextResponse.json({
      data: items,
      items: items,
      total: items.length,
      pagination: {
        limit: items.length,
        offset: 0,
        total: items.length,
        has_more: false,
      },
      meta: { request_id: `req-${Date.now()}` },
    });
  } catch (error) {
    console.error("GET observations error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch observations" },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
