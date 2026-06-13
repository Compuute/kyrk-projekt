// Privacy-preserving aggregate metrics beacon (YELLOW zone).
//
// Stores ONLY anonymous daily counters in the kyrka_metrics KV namespace.
// It never reads or sets cookies, never stores an IP address, an identifier,
// or any PII. The event name is validated against a fixed allowlist on ingress
// (RED/YELLOW rule: no free-form values can ride in), so the endpoint cannot be
// turned into a free-text sink. See docs/26-pwa-metrics-and-mobile-decision.md
// and the zone model in docs/01-architecture-red-yellow-green.md.

const ALLOWED_EVENTS = [
  "app_open",     // a device opened the PWA (deduped to once per UTC day client-side)
  "pwa_install",  // the PWA was installed to the home screen
  "push_prompt",  // the notification permission prompt was shown
  "push_grant",   // the user allowed notifications
  "push_deny",    // the user blocked/dismissed notifications
  "retain_w1",    // a device was still active 1 week after first open
  "retain_w2",    // ... 2 weeks
  "retain_w4",    // ... 4 weeks
  "retain_w12",   // ... 12 weeks
];

function utcDay(now: Date): string {
  return now.toISOString().slice(0, 10); // YYYY-MM-DD (UTC)
}

export async function onRequestPost(context: any) {
  let event = "";
  try {
    const body = await context.request.json();
    event = typeof body?.e === "string" ? body.e : "";
  } catch {
    const url = new URL(context.request.url);
    event = url.searchParams.get("e") || "";
  }

  // Ingress validation. Anything not on the allowlist is silently dropped —
  // we never echo input back and never error-leak, so the endpoint cannot be
  // probed or used to store arbitrary data.
  if (!ALLOWED_EVENTS.includes(event)) {
    return new Response(null, { status: 204 });
  }

  const kv = context.env.kyrka_metrics;
  if (kv) {
    const key = `m:${utcDay(new Date())}:${event}`;
    const current = parseInt((await kv.get(key)) || "0", 10) || 0;
    // 90-day TTL: counters are decision-grade and transient, not an archive.
    await kv.put(key, String(current + 1), { expirationTtl: 60 * 60 * 24 * 90 });
  }

  return new Response(null, {
    status: 204,
    headers: { "Access-Control-Allow-Origin": "*" },
  });
}

// Aggregate read for internal reporting, gated by a server-side token held in
// the METRICS_TOKEN secret. There is no PII to return — only counters — but we
// still 404 without a matching token so the endpoint is not publicly listable.
export async function onRequestGet(context: any) {
  const token = context.env.METRICS_TOKEN;
  const provided = context.request.headers.get("x-metrics-token");
  if (!token || provided !== token) {
    return new Response("Not found", { status: 404 });
  }

  const kv = context.env.kyrka_metrics;
  const out: Record<string, number> = {};
  if (kv) {
    const list = await kv.list({ prefix: "m:" });
    for (const k of list.keys) {
      out[k.name] = parseInt((await kv.get(k.name)) || "0", 10) || 0;
    }
  }
  return new Response(JSON.stringify(out), {
    headers: { "Content-Type": "application/json" },
  });
}
