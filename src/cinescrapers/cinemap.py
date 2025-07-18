import folium
from pathlib import Path
from cinescrapers.cinema_details import CINEMAS


def generate_cinema_map() -> None:
    """Generate a map that shows cinema markers with current showtime counts."""

    output_path = Path(__file__).parent / "cinema_map.html"

    # Calculate center as midpoint of outer cinemas
    lats = [c.latitude for c in CINEMAS]
    lons = [c.longitude for c in CINEMAS]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2

    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap"
    )

    # Add markers for each cinema
    for cinema in CINEMAS:
        icon = "film"
        color = "green"

        # Create popup HTML
        popup_html = f"""
        <div style="width: 300px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #333;">{cinema.name}</h3>
            <p style="margin: 5px 0;"><strong>Address:</strong> {cinema.address or "N/A"}</p>
            <p style="margin: 5px 0;"><strong>Phone:</strong> {cinema.phone or "N/A"}</p>
            <div style="margin: 10px 0;">
                <a href="/cinemas/{cinema.shortname}" target="_blank" 
                   style="display: inline-block; padding: 8px 12px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">
                   View Cinema Details
                </a>
                <a href="{cinema.url}" target="_blank" 
                   style="display: inline-block; padding: 8px 12px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">
                   Official Website
                </a>
            </div>
        </div>
        """

        # Add marker to map
        folium.Marker(
            location=[cinema.latitude, cinema.longitude],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{cinema.name}",
            icon=folium.Icon(color=color, icon=icon, prefix="fa"),
        ).add_to(m)

        # Add label
        folium.Marker(
            location=[cinema.latitude, cinema.longitude],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 1.5rem; font-weight: bold; color: #333; white-space: nowrap; text-align: center; text-shadow: 0px 0px 4px rgba(255,255,255,1);">{cinema.shortname}</div>',
                icon_size=(100, 20),
                icon_anchor=(50, 0),
            ),
        ).add_to(m)

    # Save map to file
    m.save(output_path)
    print(f"Cinema map saved to: {output_path}")
