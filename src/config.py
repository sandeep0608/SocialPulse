"""
Project configuration — the one place to describe your accounts.

`CHANNEL_MAP` maps a (network, profile) pair as it appears in the VistaSocial /
native export to a stable, human-readable *channel* key. A "channel" is one brand
property on one platform (e.g. the Nimbus brand's LinkedIn page). Everything in
the dashboard — the channel leaderboard, the per-channel readouts, the "Ask the
data" lookups — keys off these names, so this is the only file you edit when a
new account comes online.

If a (network, profile) pair shows up that isn't listed here, the pipeline keeps
going and labels it "<network>-unmapped" so you notice it and add a row, rather
than crashing mid-report.
"""

# ----------------------------------------------------------------------------
# Platform display names + ordering (left to right / top to bottom in the UI).
# ----------------------------------------------------------------------------
PLATFORMS = ["LinkedIn", "Instagram", "YouTube", "TikTok", "Twitter/X", "Facebook"]

# Normalise the many spellings an export uses for a network into one display name.
PLATFORM_MAP = {
    "linkedin": "LinkedIn",
    "instagram": "Instagram",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "twitter": "Twitter/X",
    "twitter/x": "Twitter/X",
    "x": "Twitter/X",
    "facebook": "Facebook",
    "meta": "Facebook",
}

# ----------------------------------------------------------------------------
# (network, profile) -> channel key.  Edit this when an account is added.
# The sample data ships for a fictional brand, "Nimbus", with two properties:
#   * "Nimbus"       — the main brand handle
#   * "Nimbus Learn" — its education arm
# ----------------------------------------------------------------------------
CHANNEL_MAP = {
    ("LinkedIn",  "Nimbus"):        "linkedin-nimbus",
    ("LinkedIn",  "Nimbus Learn"):  "linkedin-nimbuslearn",
    ("Instagram", "Nimbus"):        "instagram-nimbus",
    ("Instagram", "Nimbus Learn"):  "instagram-nimbuslearn",
    ("YouTube",   "Nimbus"):        "youtube-nimbus",
    ("YouTube",   "Nimbus Learn"):  "youtube-nimbuslearn",
    ("TikTok",    "Nimbus"):        "tiktok-nimbus",
    ("Twitter/X", "Nimbus"):        "x-nimbus",
    ("Twitter/X", "Nimbus Learn"):  "x-nimbuslearn",
    ("Facebook",  "Nimbus"):        "facebook-nimbus",
    ("Facebook",  "Nimbus Learn"):  "facebook-nimbuslearn",
}


def normalise_platform(network: str) -> str:
    """Map a raw network string to a canonical platform display name."""
    if network is None:
        return "Unknown"
    return PLATFORM_MAP.get(str(network).strip().lower(), str(network).strip())


def channel_for(platform: str, profile: str) -> str:
    """Resolve a (platform, profile) pair to a channel key, tolerant of the unknown."""
    key = CHANNEL_MAP.get((platform, str(profile).strip()))
    if key:
        return key
    slug = str(profile).strip().lower().replace(" ", "")
    return f"{platform.split('/')[0].lower()}-{slug or 'unmapped'}"
