/**
 * Render a JSON-LD structured data script for rich Google snippets.
 * Usage: <StructuredData data={{ "@context": "https://schema.org", "@type": "...", ... }} />
 */

type JsonLd = Record<string, unknown>;

export function StructuredData({ data }: { data: JsonLd }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
