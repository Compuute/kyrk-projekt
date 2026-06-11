class ConfigInjector {
  constructor(private config: string) {}
  element(element: any) {
    element.append(`<script>window.__KYRK_CONFIG__ = ${this.config};</script>`, { html: true });
  }
}

class LanguageToggler {
  constructor(private lang: 'sv' | 'am') {}
  element(element: any) {
    if (element.tagName === "body") {
      element.setAttribute("data-lang", this.lang);
    }
  }
}

class ElementSelector {
  constructor(private targetId: string, private shouldActivate: boolean) {}
  element(element: any) {
    const currentClass = element.getAttribute("class") || "";
    if (this.shouldActivate) {
      if (!currentClass.includes("active")) {
        element.setAttribute("class", (currentClass + " active").trim());
      }
    } else {
      element.setAttribute("class", currentClass.replace(" active", "").trim());
    }
  }
}

class LinkRewriter {
  constructor(private prefix: string) {}
  element(element: any) {
    const href = element.getAttribute("href");
    if (!href) return;
    
    // Ignore anchors, external URLs, and non-HTTP links (tel, mailto, swish)
    if (
      href.startsWith("#") || 
      href.includes("://") || 
      href.startsWith("mailto:") || 
      href.startsWith("tel:") || 
      href.startsWith("swish:")
    ) {
      return;
    }
    
    if (href.startsWith("/")) {
      element.setAttribute("href", this.prefix + href);
    } else if (href.startsWith("./")) {
      element.setAttribute("href", this.prefix + href.substring(1));
    }
  }
}

export async function onRequest(context: any) {
  const url = new URL(context.request.url);
  const path = url.pathname;

  // Bypass processing for static assets
  if (path.match(/\.(js|css|png|jpg|jpeg|gif|svg|ico|json|xml|txt|webmanifest)$/)) {
    return context.next();
  }

  const hasSv = path.startsWith("/sv/") || path === "/sv";
  const hasAm = path.startsWith("/am/") || path === "/am";

  // 1. Redirect if path does not have language prefix
  if (!hasSv && !hasAm) {
    const cookieStr = context.request.headers.get("Cookie") || "";
    const langMatch = cookieStr.match(/selected_language=([^;]+)/);
    let lang = langMatch ? langMatch[1] : null;

    if (!lang) {
      const acceptLang = context.request.headers.get("Accept-Language") || "";
      lang = acceptLang.toLowerCase().startsWith("am") ? "am" : "sv";
    }

    // Redirect to prefixed path, preserving original search params and subpath
    const targetPath = `/${lang}${path === "/" ? "/" : path}`;
    url.pathname = targetPath;
    return Response.redirect(url.toString(), 302);
  }

  // 2. Identify selected language
  const lang = path.startsWith("/am") ? "am" : "sv";
  const prefix = `/${lang}`;
  
  // Rewrite request URL internally to load the correct base static HTML
  const basePagePath = path.substring(prefix.length) || "/";
  const rewrittenUrl = new URL(context.request.url);
  rewrittenUrl.pathname = basePagePath;
  
  // Execute request against static asset builder
  const res = await context.env.ASSETS.fetch(rewrittenUrl);
  const contentType = res.headers.get("Content-Type") || "";

  if (contentType.includes("text/html")) {
    const cookieStr = context.request.headers.get("Cookie") || "";
    const churchMatch = cookieStr.match(/selected_church=([^;]+)/);
    const church = churchMatch ? churchMatch[1] : "nacka";
    
    // Retrieve configuration from KV
    const config = await context.env.kyrka_content.get(church) || "null";
    
    // Inject stylesheet to toggle appropriate language display classes immediately
    const styleTag = lang === 'am' 
      ? `<style>.sv { display: none !important; } .am { display: block !important; }</style>`
      : `<style>.am { display: none !important; } .sv { display: block !important; }</style>`;
    
    const response = new HTMLRewriter()
      .on("head", {
        element(el) {
          el.append(styleTag, { html: true });
        }
      })
      .on("head", new ConfigInjector(config))
      .on("body", new LanguageToggler(lang))
      .on("a", new LinkRewriter(prefix))
      .on("#lang-sv", new ElementSelector("lang-sv", lang === "sv"))
      .on("#lang-am", new ElementSelector("lang-am", lang === "am"))
      .transform(res);
      
    // Return modified response and set the selected language preference cookie
    const newRes = new Response(response.body, response);
    newRes.headers.set("Set-Cookie", `selected_language=${lang}; path=/; max-age=31536000; SameSite=Lax`);
    return newRes;
  }
  
  return res;
}
