"""Organisation-level seed: settings, offices, proof points, partners, certification."""

from ..models import Certification, Office, Partner, SiteSettings, Stat

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

STATS = [
    dict(group="about", value="2012", label="Founded",
         caption="Hyderabad, with one workshop and one idea.", order=1),
    dict(group="about", value="1,750+", label="Installations", count_from="0",
         caption="Across homes, hospitals, hotels and factories.", order=2),
    dict(group="about", value="95–100", label="People",
         caption="Engineers, fabricators, installers, service crew.", order=3),
    dict(group="about", value="24/7", label="After-sales support",
         caption="Breakdown cover, every day of the year.", order=4),
    dict(group="about", value="ISO", label="Certified",
         caption="Quality management across design and manufacture.", order=5),

    dict(group="projects", value="1,750+", label="Installations", count_from="0", order=1),
    dict(group="projects", value="2012", label="Building since", order=2),
    dict(group="projects", value="6", label="Building sectors", order=3),

    dict(group="home", value="1,750+", label="Lifts installed", count_from="0", order=1),
    dict(group="home", value="13", label="Years building", order=2),
    dict(group="home", value="24/7", label="Service cover", order=3),
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

CERTIFICATIONS = [
    dict(
        name="ISO 9001 — Quality Management System",
        issuer="Independent certification body",
        reference="Certificate available on request",
        description=(
            "Design, manufacture, installation and servicing of passenger and goods lifts "
            "operate under a documented quality management system, audited annually."
        ),
        order=1,
    ),
    dict(
        name="Load and overspeed testing",
        issuer="In-house test bench",
        description=(
            "Every car is load-tested to 125% of rated capacity, and the overspeed governor "
            "and safety gear are tripped and verified before dispatch."
        ),
        order=2,
    ),
    dict(
        name="Lift inspection and licensing",
        issuer="Telangana State Electrical Inspectorate",
        description=(
            "Installations are prepared for, and handed over against, statutory inspection "
            "and licensing under the applicable state lift rules."
        ),
        order=3,
    ),
]


def run():
    s = SiteSettings.load()
    for k, v in SETTINGS.items():
        setattr(s, k, v)
    s.save()

    for row in OFFICES:
        Office.objects.update_or_create(kind=row["kind"], defaults=row)
    for row in STATS:
        Stat.objects.update_or_create(
            group=row["group"], label=row["label"], defaults=row
        )
    for row in PARTNERS:
        Partner.objects.update_or_create(name=row["name"], defaults=row)
    for row in CERTIFICATIONS:
        Certification.objects.update_or_create(name=row["name"], defaults=row)

    return {
        "offices": Office.objects.count(),
        "stats": Stat.objects.count(),
        "partners": Partner.objects.count(),
        "certifications": Certification.objects.count(),
    }
