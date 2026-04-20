"""
Gap Miner: analyses failed queries and generates harvest seeds to fill capability gaps.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


def analyse_gaps(failed_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Given a list of failed query records, return a ranked list of
    capability gaps (unique unfulfilled goals).
    """
    goals = [q.get("user_goal", "") or q.get("failed_query", "") for q in failed_queries]
    counts = Counter(goals)
    gaps = []
    for goal, freq in counts.most_common():
        if goal:
            gaps.append({"goal": goal, "frequency": freq, "status": "pending"})
    return gaps


def generate_seeds(gap: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Given a gap description, suggest seed URLs to harvest.
    This is a heuristic approach – in production, augment with web search.
    """
    goal = gap.get("goal", "").lower()
    seeds = []

    keyword_map = {
        "image": [
            {"name": "cloudinary", "url": "https://cloudinary.com/documentation/image_transformations", "priority": "high"},
            {"name": "replicate", "url": "https://replicate.com/docs/reference/http", "priority": "medium"},
        ],
        "payment": [
            {"name": "stripe", "url": "https://docs.stripe.com/llms.txt", "priority": "high"},
        ],
        "email": [
            {"name": "sendgrid", "url": "https://docs.sendgrid.com/api-reference", "priority": "high"},
            {"name": "resend", "url": "https://resend.com/docs/api-reference/introduction", "priority": "medium"},
            {"name": "loops", "url": "https://loops.so/docs/api-reference/intro", "priority": "low"},
        ],
        "sms": [
            {"name": "twilio", "url": "https://www.twilio.com/docs/sms", "priority": "high"},
        ],
        "github": [
            {"name": "github", "url": "https://docs.github.com/en/rest", "priority": "high"},
        ],
        "database": [
            {"name": "supabase", "url": "https://supabase.com/docs/reference/javascript", "priority": "medium"},
            {"name": "airtable", "url": "https://airtable.com/developers/web/api/introduction", "priority": "medium"},
            {"name": "planetscale", "url": "https://api-docs.planetscale.com/", "priority": "low"},
        ],
        "search": [
            {"name": "elasticsearch", "url": "https://www.elastic.co/docs/api", "priority": "medium"},
        ],
        "file": [
            {"name": "s3", "url": "https://docs.aws.amazon.com/AmazonS3/latest/API", "priority": "medium"},
        ],
        "message": [
            {"name": "slack", "url": "https://api.slack.com/methods", "priority": "high"},
            {"name": "twilio", "url": "https://www.twilio.com/docs/sms", "priority": "medium"},
        ],
        "notification": [
            {"name": "slack", "url": "https://api.slack.com/methods", "priority": "high"},
        ],
        "note": [
            {"name": "notion", "url": "https://developers.notion.com/reference/intro", "priority": "high"},
        ],
        "task": [
            {"name": "linear", "url": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api", "priority": "medium"},
            {"name": "jira", "url": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/", "priority": "medium"},
        ],
        "issue": [
            {"name": "linear", "url": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api", "priority": "medium"},
            {"name": "jira", "url": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/", "priority": "medium"},
        ],
        "ai": [
            {"name": "openai", "url": "https://platform.openai.com/docs/api-reference", "priority": "high"},
            {"name": "anthropic", "url": "https://docs.anthropic.com/en/api/getting-started", "priority": "high"},
            {"name": "huggingface", "url": "https://huggingface.co/docs/api-inference/index", "priority": "medium"},
        ],
        "llm": [
            {"name": "openai", "url": "https://platform.openai.com/docs/api-reference", "priority": "high"},
            {"name": "anthropic", "url": "https://docs.anthropic.com/en/api/getting-started", "priority": "high"},
        ],
        "monitor": [
            {"name": "datadog", "url": "https://docs.datadoghq.com/api/latest/", "priority": "medium"},
            {"name": "sentry", "url": "https://docs.sentry.io/api/", "priority": "medium"},
            {"name": "pagerduty", "url": "https://developer.pagerduty.com/api-reference/", "priority": "medium"},
        ],
        "deploy": [
            {"name": "vercel", "url": "https://vercel.com/docs/rest-api", "priority": "medium"},
        ],
        "cache": [
            {"name": "upstash", "url": "https://upstash.com/docs/redis/features/restapi", "priority": "low"},
        ],
        "location": [
            {"name": "google_maps", "url": "https://developers.google.com/maps/documentation/geocoding/requests-geocoding", "priority": "medium"},
        ],
        "weather": [
            {"name": "weather_openmeteo", "url": "https://open-meteo.com/en/docs", "priority": "low"},
        ],
        "news": [
            {"name": "newsapi", "url": "https://newsapi.org/docs/endpoints", "priority": "low"},
        ],
    }

    for keyword, suggestions in keyword_map.items():
        if keyword in goal:
            seeds.extend(suggestions)

    # Deduplicate by URL
    seen = set()
    unique = []
    for seed in seeds:
        if seed["url"] not in seen:
            seen.add(seed["url"])
            unique.append(seed)

    return unique
