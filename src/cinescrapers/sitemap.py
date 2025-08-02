import datetime
from pathlib import Path

from cinescrapers.cinema_details import CINEMAS


def generate_sitemap():
    """Generate a sitemap.xml file"""
    output_path = Path(__file__).parent / "sitemap.xml"
    template_path = Path(__file__).parent / "sitemap.xml.template"
    template = template_path.read_text()

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
    output_path.write_text(sitemap_content)
    print(f"Sitemap generated at {output_path}")
