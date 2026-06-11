module.exports = function(eleventyConfig) {
  var portal = "frontend/member-portal";

  eleventyConfig.addPassthroughCopy({
    [portal + "/app.js"]: "app.js",
    [portal + "/calendar-engine.js"]: "calendar-engine.js",
    [portal + "/styles.css"]: "styles.css",
    [portal + "/sw.js"]: "sw.js",
    [portal + "/_headers"]: "_headers",
    [portal + "/_redirects"]: "_redirects",
    [portal + "/robots.txt"]: "robots.txt",
    [portal + "/sitemap.xml"]: "sitemap.xml",
    [portal + "/manifest.json"]: "manifest.json",
    [portal + "/content.json"]: "content.json",
    [portal + "/churches.json"]: "churches.json",
    [portal + "/churches"]: "churches",
    [portal + "/icons"]: "icons",
    [portal + "/fonts"]: "fonts"
  });

  return {
    dir: {
      input: portal + "/src/pages",
      output: portal + "/dist",
      includes: "../_includes"
    }
  };
};
