import { NextRequest, NextResponse } from "next/server";
import { getDocuments } from "@/lib/fixtures/case-fixtures";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  try {
    const { patientId } = await context.params;
    const searchParams = request.nextUrl.searchParams;
    const document_type = searchParams.get("document_type") || undefined;
    const search = searchParams.get("search") || undefined;

    const items = getDocuments(patientId, { document_type, search });

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
    console.error("GET documents error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch documents" },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
