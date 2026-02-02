"""
Data pipeline jobs.

Standalone tasks that can be run via CLI or scheduled with cron.
Each job does one thing: fetch, transform, or generate output.

Pattern inspired by Django management commands, Airflow tasks, dbt models.

Run jobs via CLI:
    butterfly-planner job fetch-inat --place=Oregon --year=2024
    butterfly-planner job build-species-list
    butterfly-planner job export-geojson

Or schedule with cron:
    0 2 * * 0 butterfly-planner job fetch-inat --place=Oregon  # Weekly Sunday 2am

Jobs should:
- Be idempotent (safe to re-run)
- Log progress
- Write output to data/ directory
- Handle failures gracefully
"""
