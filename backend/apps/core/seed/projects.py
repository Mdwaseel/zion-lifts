"""Project seed — seven real Zion installations, drawn from the delivered films.

Names, locations and building types come from the footage itself. Capacities,
stop counts and drive types are reasonable readings of what the films show and
should be confirmed against Zion's job records before launch.
"""

from apps.catalog.models import LiftType
from apps.projects.models import Project, ProjectCategory, ProjectImage

from . import media as M

CATEGORIES = [
    ("residential", "Residential", "Villas, private homes and apartment buildings."),
    ("hospitality", "Hospitality", "Restaurants, cafes and hotels."),
    ("healthcare", "Healthcare", "Hospitals, clinics and diagnostic centres."),
    ("commercial", "Commercial", "Offices, retail and mixed-use buildings."),
    ("institutional", "Institutional", "Government, education and public buildings."),
    ("industrial", "Industrial", "Factories, warehouses and parking structures."),
]

PROJECTS = [
    dict(
        slug="lekha-nilayam", name="Lekha Nilayam", category="residential",
        lift="home-elevator", location="Hyderabad, Telangana", year=2024, order=1,
        is_featured=True, is_portrait=False,
        statement="A glass lift set into the spine of a family house.",
        summary=(
            "A four-level private residence where the lift sits in the main circulation hall, "
            "glazed on three sides so it reads as part of the stair rather than a service riser."
        ),
        challenge=(
            "The lift had to land in the middle of the house, next to the staircase, without "
            "blocking the light that runs down through the hall. A solid shaft in that position "
            "would have cut the ground floor in two."
        ),
        solution=(
            "A machine-room-less home lift in a structural glass shaft, with a bronze-finished cabin "
            "and a starlight ceiling. The frame was detailed as slim as the structure allowed and "
            "the drive was mounted at the shaft head so nothing sits above the roof line."
        ),
        result=(
            "The hall keeps its full height and daylight, and every level of the house is reachable "
            "without touching the stair. The lift has run daily since handover."
        ),
        system="Home Elevator — MRL gearless traction", capacity="408 kg / 6 persons",
        stops="4 stops", door="Automatic centre-opening, glass",
        drive="Machine-room-less gearless", scope="Design, supply, installation and AMC",
        hero=M.frame("lekha-exterior"), poster=M.poster("lekha-nilayam"),
        video=M.video("lekha-nilayam"), loop=M.video("lekha-nilayam", loop=True),
        images=[
            ("site", "lekha-aerial", "The house from above"),
            ("site", "lekha-approach", "Approach and entrance"),
            ("interior", "lekha-hall", "Circulation hall with the glazed shaft"),
            ("interior", "lekha-cabin", "Bronze lift in the hall"),
            ("detail", "lekha-cop", "Lift operating panel"),
            ("detail", "lekha-ceiling", "Starlight ceiling"),
            ("completion", "lekha-inuse", "The lift in daily use"),
            ("completion", "lekha-corridor", "Landing on an upper floor"),
        ],
    ),
    dict(
        slug="lacheta-nivas", name="Lacheta Nivas", category="residential",
        lift="home-elevator", location="Hyderabad, Telangana", year=2024, order=2,
        is_featured=True, is_portrait=True,
        statement="Brass, marble, and a lift detailed like furniture.",
        summary=(
            "A private residence where the lift interior was specified alongside the joinery — "
            "antique brass walls, a marble floor and an indirect cove ceiling."
        ),
        challenge=(
            "The client wanted the lift to disappear into a heavily detailed interior. A standard "
            "stainless lift would have read as the only piece of equipment in the house."
        ),
        solution=(
            "An antique brass lift with a marble floor, a cove-lit ceiling and a slim vertical "
            "control panel, set behind brass-framed automatic doors that align with the surrounding "
            "stone."
        ),
        result=(
            "From the hall, the lift entrance reads as another framed opening in the wall. The "
            "brass has been specified in a brushed finish so handling marks weather in rather than out."
        ),
        system="Home Elevator — MRL gearless traction", capacity="340 kg / 5 persons",
        stops="3 stops", door="Automatic centre-opening, brass finish",
        drive="Machine-room-less gearless", scope="Design, supply, installation and AMC",
        hero=M.frame("lacheta-lobby"), poster=M.poster("lacheta-nivas"),
        video=M.video("lacheta-nivas"), loop=M.video("lacheta-nivas", loop=True),
        images=[
            ("site", "lacheta-exterior", "The residence"),
            ("interior", "lacheta-lobby", "Ground floor lift lobby"),
            ("interior", "lacheta-glass", "The lift beside the stair"),
            ("detail", "lacheta-ceiling", "Cove-lit lift ceiling"),
            ("detail", "lacheta-indicator", "Floor indicator"),
            ("detail", "lacheta-cop", "Lift operating panel"),
            ("completion", "lacheta-inuse", "In daily use"),
            ("completion", "lacheta-terrace", "Terrace level"),
        ],
    ),
    dict(
        slug="kashi-yadhav-residence", name="Kashi Yadhav's Residence", category="residential",
        lift="home-elevator", location="Hyderabad, Telangana", year=2023, order=3,
        is_portrait=True,
        statement="A lift added to a finished house, without rebuilding it.",
        summary=(
            "A retrofit into an occupied home: a self-supporting glazed shaft built against the "
            "existing stair, with the drive and structure left deliberately visible."
        ),
        challenge=(
            "There was no shaft. Cutting a masonry riser through a finished four-storey house would "
            "have meant months of disruption to a family living in it."
        ),
        solution=(
            "A self-supporting steel and glass shaft erected in the stairwell void, carrying its own "
            "loads down to a new pad at the base. The lift frame, rails and gearless machine were "
            "assembled in place over a short site programme."
        ),
        result=(
            "Every floor is served without a single structural opening cut through the slab. The "
            "exposed frame and machine have become part of how the stairwell looks."
        ),
        system="Home Elevator — MRL gearless traction", capacity="272 kg / 4 persons",
        stops="4 stops", door="Automatic side-opening",
        drive="Machine-room-less gearless", scope="Survey, structural shaft, supply and installation",
        hero=M.frame("kashi-cabin"), poster=M.poster("kashi-yadhav"),
        video=M.video("kashi-yadhav"), loop=M.video("kashi-yadhav", loop=True),
        images=[
            ("site", "kashi-exterior", "The house before installation"),
            ("installation", "kashi-structure", "Self-supporting shaft structure"),
            ("installation", "kashi-drive", "Gearless machine at the shaft head"),
            ("installation", "kashi-machine", "Drive and sheave"),
            ("interior", "kashi-cabin", "The finished lift"),
            ("interior", "kashi-interior", "Landing at first floor"),
            ("detail", "kashi-lop", "Landing operating panel"),
            ("detail", "kashi-floor", "Lift flooring"),
            ("completion", "kashi-shaft", "Looking up the glazed shaft"),
            ("completion", "kashi-stair", "The lift alongside the stair"),
        ],
    ),
    dict(
        slug="chilkuru-residence", name="Chilkuru Residence", category="residential",
        lift="capsule-elevator", location="Chilkur, Hyderabad", year=2024, order=4,
        is_featured=True, is_portrait=True,
        statement="A capsule lift running the full height of a villa atrium.",
        summary=(
            "A large private villa with a double-height atrium at its centre, served by a glazed "
            "capsule lift that runs from the entrance level to a rooftop pavilion."
        ),
        challenge=(
            "The atrium was the architectural idea of the house. Any lift placed in it had to add "
            "to that volume rather than obstruct it."
        ),
        solution=(
            "A four-sided glazed capsule in a slim steel frame, positioned so the lift travels "
            "through the atrium rather than beside it, and continues up to the roof pavilion."
        ),
        result=(
            "The ride is now part of the experience of the house, and the rooftop level is as easy "
            "to reach as the ground floor."
        ),
        system="Capsule Elevator — panoramic", capacity="544 kg / 8 persons",
        stops="4 stops", door="Automatic centre-opening, glass",
        drive="Gearless traction", scope="Design, structural glazing, supply and installation",
        hero=M.frame("chilkuru-atrium"), poster=M.poster("chilkuru-residence"),
        video=M.video("chilkuru-residence"), loop=M.video("chilkuru-residence", loop=True),
        images=[
            ("site", "chilkuru-aerial", "The villa from above"),
            ("site", "chilkuru-pavilion", "Rooftop pavilion, the top landing"),
            ("interior", "chilkuru-entrance", "Entrance level"),
            ("interior", "chilkuru-corridor", "Corridor to the atrium"),
            ("interior", "chilkuru-capsule", "Capsule lift in the atrium"),
            ("interior", "chilkuru-atrium", "The shaft through the full height"),
            ("detail", "chilkuru-ceiling", "Lift ceiling"),
            ("detail", "chilkuru-panel", "Lift operating panel"),
            ("detail", "chilkuru-lop", "Landing indicator"),
        ],
    ),
    dict(
        slug="chath-restaurant", name="Chath Restaurant", category="hospitality",
        lift="passenger-elevator", location="Hyderabad, Telangana", year=2024, order=5,
        is_featured=True, is_portrait=False,
        statement="A guest lift built into the face of a restaurant.",
        summary=(
            "A multi-level restaurant where the lift sits on the street elevation, clad in the same "
            "timber as the facade and lit as part of the signage."
        ),
        challenge=(
            "Guests arriving at street level needed to reach a rooftop dining terrace quickly, "
            "during service, without walking through the kitchen floors."
        ),
        solution=(
            "A commercial passenger lift positioned on the external elevation, with timber-clad "
            "surrounds, illuminated landing indicators and a lift finished to match the interior."
        ),
        result=(
            "The terrace works as a dining floor on a normal service night, and the lift has become "
            "part of how the building presents itself after dark."
        ),
        system="Commercial Passenger Elevator", capacity="544 kg / 8 persons",
        stops="4 stops", door="Automatic centre-opening",
        drive="Gearless traction", scope="Supply, installation and annual maintenance",
        hero=M.frame("chath-facade"), poster=M.poster("chath-restaurant"),
        video=M.video("chath-restaurant"), loop=M.video("chath-restaurant", loop=True),
        images=[
            ("site", "chath-aerial", "The restaurant from above at night"),
            ("site", "chath-facade", "Street elevation"),
            ("interior", "chath-entrance", "Lift entrance at street level"),
            ("interior", "chath-cabin", "The lift"),
            ("detail", "chath-indicator", "Landing indicators"),
            ("detail", "chath-ceiling", "Lift ceiling"),
            ("completion", "chath-terrace", "Rooftop dining terrace"),
            ("completion", "chath-inuse", "A guest leaving the lift during service"),
        ],
    ),
    dict(
        slug="niloufer-cafe", name="Niloufer Cafe", category="hospitality",
        lift="passenger-elevator", location="Hyderabad, Telangana", year=2023, order=6,
        is_portrait=True,
        statement="A busy cafe that needed a lift that never stops.",
        summary=(
            "One of Hyderabad's best-known cafes, where the lift runs continuously through trading "
            "hours and downtime is measured in lost covers."
        ),
        challenge=(
            "Very high daily cycle counts in a building that cannot close for maintenance. "
            "Reliability mattered more than any single specification."
        ),
        solution=(
            "A commercial passenger lift specified above the duty actually required, with a "
            "maintenance schedule timed around trading hours and a service response commitment."
        ),
        result=(
            "The installation has run through continuous trading since handover. The client's "
            "account of it is on this page."
        ),
        system="Commercial Passenger Elevator", capacity="544 kg / 8 persons",
        stops="3 stops", door="Automatic centre-opening",
        drive="Gearless traction", scope="Supply, installation and AMC",
        hero=M.frame("niloufer-cabin"), poster=M.poster("niloufer-cafe"),
        video=M.video("niloufer-cafe"), loop=M.video("niloufer-cafe", loop=True),
        images=[
            ("interior", "niloufer-cabin", "The lift"),
            ("interior", "niloufer-interior", "Landing"),
            ("completion", "niloufer-portrait", "The client on the installation"),
        ],
    ),
    dict(
        slug="owaisi-hospitals", name="Owaisi Hospitals", category="healthcare",
        lift="hospital-elevator", location="Santosh Nagar, Hyderabad", year=2023, order=7,
        is_featured=True, is_portrait=True,
        statement="Stretcher lifts for a hospital that never closes.",
        summary=(
            "A multi-storey hospital served by a bank of stretcher-capable lifts, specified for "
            "continuous clinical traffic and dependable emergency behaviour."
        ),
        challenge=(
            "Clinical traffic does not queue politely. Trolleys, staff, visitors and equipment all "
            "share the same cores, at all hours, and a lift out of service moves patients down a stair."
        ),
        solution=(
            "Deep stretcher-capable lifts with wide clear openings, tight levelling so trolley wheels "
            "clear the sill, wipe-clean stainless interiors, and firefighter recall across the group."
        ),
        result=(
            "Beds move between floors in a single manoeuvre, and the lift group has carried the "
            "hospital's daily traffic since commissioning."
        ),
        system="Hospital Elevator — stretcher capable", capacity="1,020 kg / 15 persons",
        stops="6 stops", door="Automatic centre-opening, 1,200 mm clear",
        drive="Gearless traction", scope="Supply, installation, commissioning and 24/7 AMC",
        hero=M.frame("owaisi-lobby"), poster=M.poster("owaisi-hospitals"),
        video=M.video("owaisi-hospitals"), loop=M.video("owaisi-hospitals", loop=True),
        images=[
            ("site", "owaisi-exterior", "Owaisi Hospitals, Santosh Nagar"),
            ("interior", "owaisi-lobby", "Ground floor lift lobby"),
            ("interior", "owaisi-doors", "Lift bank"),
            ("interior", "owaisi-cabin", "Stretcher-capable lift"),
            ("detail", "owaisi-cop", "Lift operating panel"),
            ("detail", "owaisi-ceiling", "Lift ceiling and lighting"),
            ("completion", "owaisi-waiting", "Waiting area at the lift bank"),
            ("completion", "owaisi-corridor", "Ward corridor"),
        ],
    ),
]


def run():
    cats = {}
    for i, (slug, name, desc) in enumerate(CATEGORIES, 1):
        obj, _ = ProjectCategory.objects.update_or_create(
            slug=slug, defaults=dict(name=name, description=desc, order=i)
        )
        cats[slug] = obj

    lifts = {lt.slug: lt for lt in LiftType.objects.all()}

    for row in PROJECTS:
        row = dict(row)
        slug = row.pop("slug")
        images = row.pop("images", [])
        row["category"] = cats[row.pop("category")]
        row["lift_type"] = lifts.get(row.pop("lift", ""))
        row["hero_image_url"] = row.pop("hero", "")
        row["hero_video_url"] = row.pop("video", "")
        row["loop_video_url"] = row.pop("loop", "")
        row["poster_url"] = row.pop("poster", "")

        project, _ = Project.objects.update_or_create(slug=slug, defaults=row)
        project.images.all().delete()
        for i, (stage, frame_slug, caption) in enumerate(images, 1):
            ProjectImage.objects.create(
                project=project, stage=stage, image_url=M.frame(frame_slug),
                caption=caption, alt=f"{project.name} — {caption}", order=i,
            )

    return {
        "project_categories": ProjectCategory.objects.count(),
        "projects": Project.objects.count(),
        "project_images": ProjectImage.objects.count(),
    }
