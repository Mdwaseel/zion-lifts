"""Organisation-level seed: site settings, offices and component partners.

The stat rows and the certifications were seeded here too. They are static
content in ``frontend/src/data/`` now — there is no table to fill.
"""

from ..models import Office, Partner, SiteSettings

SETTINGS = dict(
    company_name="Zion Lifts",
    tagline="Engineered to rise.",
    statement="Helping people move the right way — safer, quieter, better.",
    phone="+91 75690 08004",
    phone_service="+91 75690 08004",
    whatsapp="917569008004",
    email="info@zionlifts.com",
    email_service="service@zionlifts.com",
    founded_year=2012,
    installations=1750,
    team_size="95–100",
    city="Hyderabad",
    country="India",
)

OFFICES = [
    dict(
        kind="head_office",
        name="Zion Lifts — Head Office",
        address="Zion Lifts Pvt. Ltd.\nBanjara Hills, Road No. 12",
        locality="Banjara Hills",
        city="Hyderabad",
        state="Telangana",
        postcode="500034",
        phone="+91 75690 08004",
        email="info@zionlifts.com",
        hours="Mon–Sat, 9:30 am – 6:30 pm",
        note="Design consultations and project planning.",
        latitude=17.4126,
        longitude=78.4392,
        map_embed_url=(
            "https://www.google.com/maps?q=Banjara+Hills+Hyderabad+Telangana&output=embed"
        ),
        directions_url="https://www.google.com/maps/search/?api=1&query=Banjara+Hills+Hyderabad",
        order=1,
    ),
    dict(
        kind="factory",
        name="Zion Lifts — Manufacturing Facility",
        address="Zion Lifts Manufacturing Unit\nIDA Jeedimetla",
        locality="Jeedimetla",
        city="Hyderabad",
        state="Telangana",
        postcode="500055",
        phone="+91 75690 08004",
        email="works@zionlifts.com",
        hours="Mon–Sat, 9:00 am – 6:00 pm",
        note="Fabrication, assembly and load testing. Visits by appointment.",
        latitude=17.5107,
        longitude=78.4482,
        map_embed_url=(
            "https://www.google.com/maps?q=IDA+Jeedimetla+Hyderabad+Telangana&output=embed"
        ),
        directions_url="https://www.google.com/maps/search/?api=1&query=IDA+Jeedimetla+Hyderabad",
        order=2,
    ),
]

PARTNERS = [
    dict(name="Gearless traction drives", role="drive",
         component="Permanent-magnet synchronous gearless machines", order=1),
    dict(name="VVVF drive controllers", role="controller",
         component="Closed-loop variable-voltage variable-frequency control", order=2),
    dict(name="Automatic door operators", role="door",
         component="Centre- and side-opening door systems with light curtains", order=3),
    dict(name="Progressive safety gear", role="safety",
         component="Overspeed governor, safety gear and buffers to EN 81", order=4),
    dict(name="Hydraulic power packs", role="motor",
         component="Submersible power units for low-rise hydraulic lifts", order=5),
    dict(name="Cabin finishing", role="cabin",
         component="Stainless steel, brass, glass, stone and veneer interiors", order=6),
]

def run():
    s = SiteSettings.load()
    for k, v in SETTINGS.items():
        setattr(s, k, v)
    s.save()

    for row in OFFICES:
        Office.objects.update_or_create(kind=row["kind"], defaults=row)
    for row in PARTNERS:
        Partner.objects.update_or_create(name=row["name"], defaults=row)

    return {
        "offices": Office.objects.count(),
        "partners": Partner.objects.count(),
    }
