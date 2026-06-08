module.exports = function(eleventyConfig) {
  var portal = "frontend/member-portal";

  eleventyConfig.addPassthroughCopy(portal + "/app.js");
  eleventyConfig.addPassthroughCopy(portal + "/calendar-engine.js");
  eleventyConfig.addPassthroughCopy(portal + "/styles.css");
  eleventyConfig.addPassthroughCopy(portal + "/sw.js");
  eleventyConfig.addPassthroughCopy(portal + "/_headers");
  eleventyConfig.addPassthroughCopy(portal + "/robots.txt");
  eleventyConfig.addPassthroughCopy(portal + "/sitemap.xml");
  eleventyConfig.addPassthroughCopy(portal + "/manifest.json");
  eleventyConfig.addPassthroughCopy(portal + "/content.json");
  eleventyConfig.addPassthroughCopy(portal + "/churches.json");
  eleventyConfig.addPassthroughCopy(portal + "/churches");
  eleventyConfig.addPassthroughCopy(portal + "/icons");

  return {
    dir: {
      input: portal + "/src/pages",
      output: portal + "/dist",
      includes: "../_includes"
    }
  };
};
