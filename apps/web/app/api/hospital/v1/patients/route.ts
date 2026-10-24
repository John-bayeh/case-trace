import { NextRequest, NextResponse } from "next/server";
import { getAllPatients } from "@/lib/fixtures/case-fixtures";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get("query") || searchParams.get("search") || undefined;
    const limit = parseInt(searchParams.get("limit") || "20", 10);
    const offset = parseInt(searchParams.get("offset") || "0", 10);

    const allPatients = getAllPatients(query);
    const paginated = allPatients.slice(offset, offset + limit);

    return NextResponse.json({
      data: paginated,
      items: paginated,
      total: allPatients.length,
      pagination: {
        limit,
        offset,
        total: allPatients.length,
        has_more: offset + limit < allPatients.length,
      },
      meta: {
        request_id: `req-${Date.now()}`,
      },
    });
  } catch (error) {
    console.error("GET /api/hospital/v1/patients error:", error);
    return NextResponse.json(
      {
        error: {
          code: "INTERNAL_ERROR",
          message: "Failed to retrieve patients",
        },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
