import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL || "https://cadora.pro";
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/dashboard/", "/projects/", "/billing/", "/profile/", "/settings/"],
    },
    sitemap: `${base}/sitemap.xml`,
  };
}
