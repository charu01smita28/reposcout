"""
Dry run: show exactly what text would be sent to the embedding API.
Helps verify data quality before spending API credits.

Usage:
    python scripts/dry_run_embeddings.py
    python scripts/dry_run_embeddings.py --samples 20
    python scripts/dry_run_embeddings.py --package requests
"""

import argparse
import duckdb
from pathlib import Path
from text_cleaner import build_embedding_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "reposcout.db"


def main():
    parser = argparse.ArgumentParser(description="Dry run: preview embedding texts")
    parser.add_argument("--samples", type=int, default=5, help="Number of samples to show")
    parser.add_argument("--package", type=str, default="", help="Show specific package")
    parser.add_argument("--stats", action="store_true", help="Show data quality stats")
    args = parser.parse_args()

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    if args.package:
        # Show specific package
        df = conn.execute(f"""
            SELECT
                p.package_name, p.dependent_count, p.stars, p.growth_pct,
                COALESCE(m.summary, '') AS summary,
                COALESCE(m.description, '') AS description,
                COALESCE(m.keywords, '') AS keywords,
                COALESCE(m.classifiers, '[]') AS classifiers,
                COALESCE(m.version, '') AS version,
                COALESCE(m.total_versions, 0) AS total_versions
            FROM packages p
            LEFT JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
            WHERE LOWER(p.package_name) = LOWER('{args.package}')
        """).fetchdf()
    else:
        # Top N by dependents
        df = conn.execute(f"""
            SELECT
                p.package_name, p.dependent_count, p.stars, p.growth_pct,
                COALESCE(m.summary, '') AS summary,
                COALESCE(m.description, '') AS description,
                COALESCE(m.keywords, '') AS keywords,
                COALESCE(m.classifiers, '[]') AS classifiers,
                COALESCE(m.version, '') AS version,
                COALESCE(m.total_versions, 0) AS total_versions
            FROM packages p
            LEFT JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
            WHERE COALESCE(m.summary, '') != '' OR COALESCE(m.description, '') != ''
            ORDER BY p.dependent_count DESC
            LIMIT {args.samples}
        """).fetchdf()

    packages = df.to_dict(orient="records")

    if args.stats:
        # Data quality stats
        stats = conn.execute("""
            SELECT
                COUNT(*) AS total_packages,
                SUM(CASE WHEN m.name IS NOT NULL THEN 1 ELSE 0 END) AS has_metadata,
                SUM(CASE WHEN LENGTH(COALESCE(m.summary, '')) > 0 THEN 1 ELSE 0 END) AS has_summary,
                SUM(CASE WHEN LENGTH(COALESCE(m.description, '')) > 20 THEN 1 ELSE 0 END) AS has_description,
                SUM(CASE WHEN LENGTH(COALESCE(m.keywords, '')) > 0 THEN 1 ELSE 0 END) AS has_keywords,
                SUM(CASE WHEN m.classifiers != '[]' AND m.classifiers IS NOT NULL THEN 1 ELSE 0 END) AS has_classifiers,
                ROUND(AVG(LENGTH(COALESCE(m.description, ''))), 0) AS avg_desc_length,
                MAX(LENGTH(COALESCE(m.description, ''))) AS max_desc_length,
                ROUND(MEDIAN(LENGTH(COALESCE(m.description, ''))), 0) AS median_desc_length
            FROM packages p
            LEFT JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
        """).fetchdf()

        print("=" * 70)
        print("DATA QUALITY STATS")
        print("=" * 70)
        for col in stats.columns:
            print(f"  {col:25s} : {stats[col].iloc[0]:>10,}")

        # Description length distribution
        print("\n  Description length buckets:")
        buckets = conn.execute("""
            SELECT
                CASE
                    WHEN LENGTH(COALESCE(m.description, '')) = 0 THEN 'empty'
                    WHEN LENGTH(COALESCE(m.description, '')) < 100 THEN '<100 chars'
                    WHEN LENGTH(COALESCE(m.description, '')) < 500 THEN '100-500'
                    WHEN LENGTH(COALESCE(m.description, '')) < 2000 THEN '500-2K'
                    WHEN LENGTH(COALESCE(m.description, '')) < 8000 THEN '2K-8K'
                    ELSE '8K+'
                END AS bucket,
                COUNT(*) AS count
            FROM packages p
            LEFT JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
            GROUP BY bucket
            ORDER BY count DESC
        """).fetchdf()
        print(buckets.to_string(index=False))

        # Sample of descriptions that are markdown
        print("\n  Content types:")
        types = conn.execute("""
            SELECT
                COALESCE(m.description_content_type, 'NULL') AS content_type,
                COUNT(*) AS count
            FROM packages p
            LEFT JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
            GROUP BY content_type
            ORDER BY count DESC
            LIMIT 10
        """).fetchdf()
        print(types.to_string(index=False))
        print()

    conn.close()

    # Show embedding texts
    print("=" * 70)
    print(f"EMBEDDING TEXT PREVIEW ({len(packages)} packages)")
    print("=" * 70)

    for pkg in packages:
        text = build_embedding_text(pkg)
        char_count = len(text)
        approx_tokens = char_count // 4

        summary = pkg.get("summary", "") or ""
        keywords = pkg.get("keywords", "") or ""
        classifiers = pkg.get("classifiers", "[]") or "[]"

        print(f"\n{'━' * 70}")
        print(f"PACKAGE: {pkg['package_name']}  |  dependents: {pkg['dependent_count']:,}  |  stars: {pkg['stars'] or 0:,}")
        print(f"{'━' * 70}")

        print(f"\n  RAW FIELDS:")
        print(f"    summary:     {summary!r}")
        print(f"    keywords:    {keywords!r}")
        print(f"    classifiers: {classifiers[:200]}{'...' if len(classifiers) > 200 else ''}")

        print(f"\n  FINAL EMBEDDING TEXT ({char_count} chars, ~{approx_tokens} tokens):")
        print(f"  {'─' * 60}")
        for line in text.split('\n'):
            print(f"    {line}")
        print(f"  {'─' * 60}")

    # Token estimate
    if not args.package:
        total_chars = sum(len(build_embedding_text(p)) for p in packages)
        print(f"\n{'=' * 70}")
        print(f"TOTAL for these {len(packages)} samples: {total_chars:,} chars (~{total_chars // 4:,} tokens)")


if __name__ == "__main__":
    main()
