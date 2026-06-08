module.exports = function(eleventyConfig) {
  eleventyConfig.addPassthroughCopy("frontend/member-portal/app.js");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/styles.css");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/sw.js");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/_headers");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/robots.txt");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/sitemap.xml");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/manifest.json");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/content.json");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/churches.json");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/churches");
  eleventyConfig.addPassthroughCopy("frontend/member-portal/icons");

  return {
    dir: {
      input: "frontend/member-portal/src",
      output: "frontend/member-portal/dist",
      includes: "_includes",
      data: "_data"
    }
  };
};
