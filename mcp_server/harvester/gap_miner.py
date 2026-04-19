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
        ],
        "payment": [
            {"name": "stripe", "url": "https://docs.stripe.com/llms.txt", "priority": "high"},
        ],
        "email": [
            {"name": "sendgrid", "url": "https://docs.sendgrid.com/api-reference", "priority": "high"},
        ],
        "sms": [
            {"name": "twilio", "url": "https://www.twilio.com/docs/sms", "priority": "high"},
        ],
        "github": [
            {"name": "github", "url": "https://docs.github.com/en/rest", "priority": "high"},
        ],
        "database": [
            {"name": "supabase", "url": "https://supabase.com/docs/reference/javascript", "priority": "medium"},
        ],
        "search": [
            {"name": "elasticsearch", "url": "https://www.elastic.co/docs/api", "priority": "medium"},
        ],
        "file": [
            {"name": "s3", "url": "https://docs.aws.amazon.com/AmazonS3/latest/API", "priority": "medium"},
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
