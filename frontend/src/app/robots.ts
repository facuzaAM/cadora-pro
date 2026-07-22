import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/dashboard/", "/projects/", "/billing/", "/profile/", "/settings/"],
    },
    sitemap: "https://cadora.pro/sitemap.xml",
  };
}
