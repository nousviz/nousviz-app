-- Nousviz: Seed official publisher record (P20c)
-- Inserts the Nousviz core team as the official publisher.
-- Idempotent — safe to re-run.

INSERT INTO publishers (slug, name, description, website, github_org, verified, featured)
VALUES (
    'nousviz',
    'Nousviz',
    'Core Nousviz platform team. Maintains all official plugins.',
    'https://github.com/nousviz',
    'nousviz',
    true,
    true
)
ON CONFLICT (slug) DO UPDATE SET
    name        = EXCLUDED.name,
    description = EXCLUDED.description,
    website     = EXCLUDED.website,
    github_org  = EXCLUDED.github_org,
    verified    = EXCLUDED.verified,
    featured    = EXCLUDED.featured;
