// Serves content.json dynamically from KV on the edge.
export async function onRequestGet(context: any) {
  const cookieStr = context.request.headers.get("Cookie") || "";
  const churchMatch = cookieStr.match(/selected_church=([^;]+)/);
  const church = churchMatch ? churchMatch[1] : "nacka";

  const config = await context.env.kyrka_content.get(church);
  if (!config) {
    return new Response(JSON.stringify({ error: "church config not found in KV" }), {
      status: 404,
      headers: { 
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }

  return new Response(config, {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=60"
    }
  });
}
