from pydantic import BaseModel


class DiscoveredLink(BaseModel):
    text: str
    url: str


class SiteDiscovery(BaseModel):
    website_url: str
    page_title: str
    detected_website_type: str
    visible_links: list[DiscoveredLink]
    headings: list[str]
    form_count: int
    footer_present: bool
    console_errors: list[str]
    network_errors: list[str]
    navigation_warnings: list[str]
