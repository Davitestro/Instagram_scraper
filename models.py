"""
Data models for Instagram scraping.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InstagramMedia:
    """Represents a single Instagram reel or post."""
    url: str
    shortcode: str
    caption: Optional[str] = None
    created_at: Optional[str] = None
    like_count: str = "0"
    comment_count: str = "0"
    view_count: str = "0"  # For reels/videos
    author: Optional[str] = None  # Only one author field
    media_type: str = "post"  # "reel", "post", "video"
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)  # URLs in caption
    music: Optional[str] = None  # Music used in reel
    location: Optional[str] = None
    is_video: bool = False
    thumbnail_url: Optional[str] = None


@dataclass
class InstagramComment:
    """Represents a comment on an Instagram post/reel."""
    text: str
    author: str
    author_username: str
    created_at: Optional[str] = None
    like_count: str = "0"
    reply_count: str = "0"
    replies: List['InstagramComment'] = field(default_factory=list)
    level: int = 1  # 1 = direct comment, 2 = reply to comment


@dataclass
class InstagramMediaDetails(InstagramMedia):
    """Represents a media with its comments."""
    comments: List[InstagramComment] = field(default_factory=list)


@dataclass
class InstagramProfile:
    """Represents an Instagram profile."""
    url: str
    username: str
    display_name: str = ""
    bio: str = ""
    follower_count: str = "0"
    following_count: str = "0"
    post_count: str = "0"
    is_private: bool = False
    is_verified: bool = False
    media: List[InstagramMedia] = field(default_factory=list)


@dataclass
class SearchResult:
    """Represents a search result."""
    keyword: str
    scraped_at: str
    total_media_found: int
    media_collected: int
    media_data: List[dict]