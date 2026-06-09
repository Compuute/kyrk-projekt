// Middleware to inject church config into HTML files at the edge.
class ConfigInjector {
  constructor(private config: string) {}
  element(element: any) {
    element.append(`<script>window.__KYRK_CONFIG__ = ${this.config};</script>`, { html: true });
  }
}

export async function onRequest(context: any) {
  const res = await context.next();
  const contentType = res.headers.get("Content-Type") || "";

  if (contentType.includes("text/html")) {
    const cookieStr = context.request.headers.get("Cookie") || "";
    const churchMatch = cookieStr.match(/selected_church=([^;]+)/);
    const church = churchMatch ? churchMatch[1] : "nacka";
    
    // Get config from the bound KV namespace
    const config = await context.env.kyrka_content.get(church) || "null";
    
    return new HTMLRewriter()
      .on("head", new ConfigInjector(config))
      .transform(res);
  }
  return res;
}
