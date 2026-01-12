from pathlib import Path
from dataclasses import dataclass


@dataclass
class KeywordRule:
    key: str
    value: str
    priority: int


def load_keywords(file_path):
    """
    Load keyword rules from text file.

    Format supported:
      keyword = value
      keyword = value | priority

    Example:
      নদী = river | 10
      আকাশ = sky | 1
    """

    rules = []

    path = Path(file_path)
    if not path.exists():
        return rules

    priority_counter = 1000  # default priority (higher = stronger)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # skip comments / empty
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            left, right = line.split("=", 1)
            key = left.strip()

            # optional priority support
            if "|" in right:
                value_part, priority_part = right.split("|", 1)
                value = value_part.strip()
                try:
                    priority = int(priority_part.strip())
                except ValueError:
                    priority = priority_counter
            else:
                value = right.strip()
                priority = priority_counter

            rules.append(
                KeywordRule(
                    key=key,
                    value=value,
                    priority=priority
                )
            )

            priority_counter -= 1

    # sort by priority (high → low)
    rules.sort(key=lambda r: r.priority, reverse=True)

    return rules
