import datetime

from cinescrapers.cinema_details import CINEMAS
from cinescrapers.config import SITEMAP_XML, SITEMAP_XML_TEMPLATE


def generate_sitemap():
    """Generate a sitemap.xml file"""
    template = SITEMAP_XML_TEMPLATE.read_text()

    cinema_page_sitemaps = "\n".join(
        f"""
    <url>
        <loc>https://filmhose.uk/cinemas/{cinema.shortname}</loc>
        <lastmod><!-- TODAY --></lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>

    <url>
        <loc>https://filmhose.uk/cinema-listings/{cinema.shortcode}</loc>
        <lastmod><!-- TODAY --></lastmod>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
"""
        for cinema in CINEMAS
    )
    sitemap_content = template.replace("<!-- CINEMA PAGES -->", cinema_page_sitemaps)
    sitemap_content = template.replace(
        "<!-- CINEMA PAGES -->", cinema_page_sitemaps
    ).replace("<!-- TODAY -->", datetime.datetime.now().date().isoformat())
    SITEMAP_XML.write_text(sitemap_content)
    print(f"Sitemap generated at {SITEMAP_XML}")
