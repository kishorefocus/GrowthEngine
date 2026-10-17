import { MetadataRoute } from "next";
import { seoApi } from "@/lib/api-client";

export const revalidate = 3600; // 1 hour

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = "https://www.getyourclientsb2b.com";

  // Core public URLs
  const routes: MetadataRoute.Sitemap = [
    {
      url: `${baseUrl}`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${baseUrl}/tools/subject-line-grader`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/tools/email-verifier`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/alternatives/apollo/agencies`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/find-leads/technology/austin`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
  ];

  try {
    const publishedSlugs = await seoApi.getPublicSlugs();
    // Cap at 5,000 entries per sitemap file as per specification
    const cappedSlugs = publishedSlugs.slice(0, 5000);

    for (const slug of cappedSlugs) {
      routes.push({
        url: `${baseUrl}/${slug}`,
        lastModified: new Date(),
        changeFrequency: "weekly",
        priority: 0.7,
      });
    }
  } catch {
    // Graceful fallback if backend is unavailable during static build
  }

  return routes;
}
