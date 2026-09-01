"""Editorial seed: journal, testimonials, team, awards and gallery.

The FAQ, the timeline, the service pillars and the legal pages used to be seeded
here too. They are static content in ``frontend/src/data/`` now — there is no
table to fill.
"""

from datetime import timedelta

from django.utils import timezone

from ..models import Award, BlogPost, GalleryItem, Project, TeamMember, Testimonial

from . import media as M

# --------------------------------------------------------------------- Journal

JOURNAL = [
    dict(
        slug="how-to-size-a-home-lift", title="How to size a home lift before you draw the shaft",
        category="architecture", read_minutes=7, is_featured=True, days_ago=12,
        hero=M.frame("lekha-hall"),
        excerpt=(
            "Most home lifts are sized late, once the plan is fixed and the only space left is the "
            "one nobody wanted. Here is how to do it in the other order."
        ),
        body=(
            "A lift is one of the few things in a house that cannot be moved 200 mm later. It sets "
            "a structural line from the foundation to the roof, and every floor it passes through "
            "has to agree with it. Which is why sizing it after the plan is settled tends to produce "
            "the worst lift the house could have had.\n\n"
            "## Start with the person, not the shaft\n\n"
            "The first question is not how much space you can spare. It is who has to fit inside. "
            "A four-passenger car at roughly 900 × 1,000 mm internal is fine for people walking in "
            "unaided. If anyone in the household may use a wheelchair — now or in twenty years — you "
            "need enough depth to enter, turn and face the doors, which pushes you to a six-"
            "passenger car nearer 1,100 × 1,400 mm internal.\n\n"
            "That single decision changes the shaft by about 300 mm in each direction. It is far "
            "cheaper to make now than after the slab is poured.\n\n"
            "## Then the shaft around it\n\n"
            "Add the running clearances, the car frame, the rails and the counterweight, and a "
            "four-passenger car needs an internal shaft from about 1,100 × 1,000 mm. A six-passenger "
            "car needs about 1,400 × 1,200 mm. Those are internal dimensions, plumb over the whole "
            "travel — not the dimension between the blocks before plaster.\n\n"
            "> Shafts are rarely plumb and rarely the dimension on the drawing. That is what the "
            "site survey is for.\n\n"
            "## The two dimensions people forget\n\n"
            "**Pit depth.** The space below the lowest landing, from about 350 mm on a reduced-pit "
            "home lift. It has to be tanked if there is any chance of water.\n\n"
            "**Headroom.** The space above the top landing, from about 2,600 mm. On a machine-room-"
            "less lift the machine lives in here, which is exactly why you no longer need a room "
            "above the roof.\n\n"
            "## Where to put it\n\n"
            "The best position is usually next to the stair, not far from it. People take the stair "
            "for one floor and the lift for three, and putting the two together means one "
            "circulation core instead of two. If the stair sits in a top-lit hall, a glazed shaft "
            "keeps the light coming down.\n\n"
            "## What to send an engineer\n\n"
            "A floor plan, a section, the floor-to-floor heights, and a sentence about who will use "
            "it. That is enough for a real answer. Everything else can be resolved on site."
        ),
    ),
    dict(
        slug="what-actually-stops-a-lift-falling",
        title="What actually stops a lift falling", category="safety",
        read_minutes=6, days_ago=27, hero=M.frame("kashi-drive"),
        excerpt=(
            "The single most common fear about lifts describes a failure mode that the machine is "
            "specifically built to make impossible. Here is the chain of things that would all have "
            "to fail at once."
        ),
        body=(
            "Ask people what worries them about lifts and almost all of them describe the same "
            "thing: the rope breaks and the car falls. It is worth explaining why that is not how "
            "a lift is built, because the real answer is more reassuring than any amount of "
            "reassurance.\n\n"
            "## There is never one rope\n\n"
            "A traction lift hangs on multiple independent steel ropes. Each one on its own is rated "
            "well beyond the weight of the car and everything in it. They are inspected at every "
            "service and replaced on wear, long before strength becomes a question. For all of them "
            "to fail simultaneously is not a scenario the design treats as credible.\n\n"
            "## The car is mostly balanced anyway\n\n"
            "A counterweight carries the weight of the empty car plus about half its rated load. "
            "The motor only ever moves the difference between the two sides. This is why a lift "
            "motor is far smaller than people expect, and it means the load on the ropes is a "
            "fraction of what the raw numbers suggest.\n\n"
            "## Then the part that does the real work\n\n"
            "Underneath all of that sits the safety gear, and it does not care about ropes at all.\n\n"
            "A governor rope runs alongside the car, turning a sheave as it travels. If the car ever "
            "descends faster than the trip speed, the governor grips that rope. The rope pulls a "
            "linkage on the car frame. The linkage drives steel wedges against the guide rails, and "
            "friction brings the car to a controlled stop.\n\n"
            "> No electricity. No control system. No software. A speed, a linkage and two steel "
            "wedges. It works during a power cut because it never needed power.\n\n"
            "## And below that, buffers\n\n"
            "At the base of the shaft, buffers absorb the energy of an over-travel. They are the "
            "last item in the chain, and in normal service they are never touched.\n\n"
            "## Why it is tested rather than asserted\n\n"
            "None of this is worth anything unproven, which is why every car is load-tested to 125% "
            "of rated capacity and has its governor and safety gear physically tripped before "
            "dispatch, and again after installation. The test is the point."
        ),
    ),
    dict(
        slug="machine-room-less-explained",
        title="Machine-room-less, explained without the brochure language",
        category="engineering", read_minutes=5, days_ago=41, hero=M.frame("kashi-machine"),
        excerpt=(
            "MRL is on every lift specification written this decade. What it actually changes is "
            "narrower, and more useful, than the marketing suggests."
        ),
        body=(
            "For most of the twentieth century a lift needed a room above the shaft. Inside it sat "
            "a geared traction machine: a motor, a worm gearbox and a sheave, sized to a building "
            "and bolted to a slab poured specifically for it.\n\n"
            "## What changed\n\n"
            "Permanent-magnet synchronous motors produce high torque at low speed without gear "
            "reduction. Remove the gearbox and the machine becomes small enough and light enough to "
            "mount on the guide rails at the head of the shaft. The controller becomes a cabinet "
            "beside a landing door.\n\n"
            "The room disappears. On a residential building that is a floor of usable area returned "
            "to the client, and a roof line that no longer has a box on it.\n\n"
            "## The part that matters more\n\n"
            "The space saving is what sells MRL. The gearbox removal is what improves it.\n\n"
            "A worm gearbox is the noisiest component in a traditional lift, the main heat source, "
            "and the reason for oil changes. Take it out and a passenger lift runs under about "
            "52 dB(A) in the car — quiet enough to sit beside a bedroom, which is exactly where home "
            "lifts end up.\n\n"
            "> The gearless motor is why a modern lift is quiet. The missing room is just the part "
            "you can point at on a drawing.\n\n"
            "## What it does not solve\n\n"
            "MRL does not remove the need for headroom — the machine lives in it. It does not suit "
            "every load case: very heavy goods duty over a short travel is still often better served "
            "hydraulically. And it puts the machine in the shaft, so maintenance access has to be "
            "designed rather than assumed.\n\n"
            "## When to specify it\n\n"
            "For essentially every new passenger lift up to about twenty floors. The exceptions are "
            "the ones worth arguing about, and they are exceptions."
        ),
    ),
    dict(
        slug="retrofitting-a-lift-into-a-finished-house",
        title="Retrofitting a lift into a house that is already finished",
        category="projects", read_minutes=6, days_ago=58, hero=M.frame("kashi-structure"),
        excerpt=(
            "There was no shaft, the family was living there, and cutting a masonry riser through "
            "four floors was not an option. What we did instead."
        ),
        body=(
            "Kashi Yadhav's residence is a four-storey house in Hyderabad that was never built for "
            "a lift. By the time we were asked, it was finished, occupied and fully furnished.\n\n"
            "## The obvious answer was the wrong one\n\n"
            "The conventional route is to cut a shaft: open the slabs, build a masonry riser, make "
            "good. In an occupied house that is months of dust, structural propping and a family "
            "living around a hole through the middle of their home.\n\n"
            "## What we built instead\n\n"
            "A self-supporting steel shaft, erected in the void beside the existing staircase. It "
            "carries its own loads down to a new pad at the base, so the existing slabs carry "
            "nothing they were not already carrying. The slabs are penetrated only where the landing "
            "doors need to pass through.\n\n"
            "The infill is glass. That was partly architectural — the stairwell keeps its light — "
            "and partly practical, because a glazed frame is lighter than a clad one.\n\n"
            "## Sequencing around a household\n\n"
            "The stair had to stay usable throughout, so the structure was assembled in sections "
            "from the base upward, and the noisy operations — drilling the base pad, fixing the "
            "rail brackets — were programmed and agreed rather than sprung on the family.\n\n"
            "> Every floor is now served, and not one structural opening was cut through the house.\n\n"
            "## What we would tell the next client\n\n"
            "A retrofit is a survey problem before it is an engineering problem. Almost everything "
            "that goes wrong on these jobs is a dimension nobody checked: a stairwell that narrows "
            "at the third floor, a beam in the wrong place, a floor-to-floor height that differs "
            "from the one below it. Measure first, quote second."
        ),
    ),
    dict(
        slug="what-an-amc-should-actually-include",
        title="What a lift maintenance contract should actually include",
        category="maintenance", read_minutes=5, days_ago=73, hero=M.frame("lacheta-cop"),
        excerpt=(
            "Most AMC disputes come from the same place: nobody agreed what a visit was for. A "
            "short guide to reading the contract you are about to sign."
        ),
        body=(
            "A maintenance contract is the part of a lift purchase people compare on price alone, "
            "and it is the part where price alone tells you least. Two contracts with the same "
            "annual figure can mean very different things.\n\n"
            "## Comprehensive or not\n\n"
            "The first thing to establish. A comprehensive contract includes parts; a "
            "non-comprehensive one covers labour and bills parts separately. Neither is wrong, but "
            "a non-comprehensive contract will always look cheaper on the day you sign it.\n\n"
            "## Visit frequency, tied to usage\n\n"
            "Monthly for commercial and healthcare installations. Quarterly at minimum for a home "
            "lift that runs a few times a day. Frequency should follow duty cycle, not the "
            "calendar.\n\n"
            "## What is actually done on a visit\n\n"
            "Ask for the checklist. A real preventive visit covers rope condition and tension, brake "
            "adjustment and lining wear, door operator timing and the light curtain, levelling "
            "accuracy, guide shoes, the pit and its buffers, and the emergency intercom.\n\n"
            "> If the intercom is not on the list, the contract is not serious. It is the one "
            "component whose failure you only discover at the worst possible moment.\n\n"
            "## Safety testing, in writing\n\n"
            "The overspeed governor and safety gear should be tested on a stated schedule and the "
            "result recorded. A contract that never trips the safety gear is not testing the thing "
            "that matters most.\n\n"
            "## Response times that mean something\n\n"
            "An entrapment is not the same call as a noisy door. The contract should say so, with "
            "separate response commitments and an out-of-hours number that a person answers.\n\n"
            "## Parts availability\n\n"
            "Ask how long parts are supported for the system being installed. This is the question "
            "that decides whether year fifteen is a service call or an argument."
        ),
    ),
    dict(
        slug="designing-a-lift-people-look-at",
        title="Designing a lift people are meant to look at",
        category="architecture", read_minutes=6, days_ago=95, hero=M.frame("chilkuru-atrium"),
        excerpt=(
            "A capsule lift stops being building services and becomes part of the room. That "
            "changes almost every decision about how it is built."
        ),
        body=(
            "Most lifts are designed to be unnoticed. A capsule lift is the opposite: it sits in "
            "the middle of an atrium with nothing hidden, and everything that would normally be "
            "buried in a masonry shaft is on display.\n\n"
            "## The structure becomes the detail\n\n"
            "In a conventional shaft, the frame only has to be strong. In a glazed shaft it has to "
            "be strong and thin, because every millimetre of steel is a millimetre of view "
            "obstructed. Members are sized to the sightline as much as the load, and the connections "
            "are designed to be seen from below.\n\n"
            "## Cable management is architecture now\n\n"
            "Travelling cables, governor rope, limit switches and door harnesses all still exist. "
            "In a glazed lift they are routed inside the frame sections rather than clipped to the "
            "outside of them. This is the single biggest difference between a capsule lift that "
            "looks considered and one that looks like a machine in a glass box.\n\n"
            "## Glass that fails safely\n\n"
            "Both the car and the shaft glazing are toughened and laminated. Toughened so it breaks "
            "into blunt fragments, laminated so an interlayer holds those fragments in place rather "
            "than dropping them into an atrium.\n\n"
            "> At Chilkuru Residence the car runs through the atrium rather than beside it. The ride "
            "is part of the experience of the house.\n\n"
            "## Where the light comes from\n\n"
            "A glazed car cannot rely on wall-mounted fittings — there are no walls. Lighting moves "
            "to the ceiling and the floor perimeter, and at night the shaft itself becomes a lit "
            "element in the room, which needs deciding early rather than discovered later.\n\n"
            "## The trade you are making\n\n"
            "A capsule lift needs a larger shaft than a solid one of the same capacity, and it costs "
            "more. What you get back is a piece of the building rather than a piece of plant."
        ),
    ),
]

# ----------------------------------------------------------------- Testimonials
TESTIMONIALS = [
    dict(name="Niloufer Cafe", role="Owner", organisation="Niloufer Cafe",
         location="Hyderabad", project="niloufer-cafe", is_featured=True, order=1,
         video=M.video("niloufer-cafe"), poster=M.poster("niloufer-cafe"),
         quote=(
             "We run all day, every day, and we cannot close for repairs. The lift has kept working "
             "through that, and when we have called, someone has answered."
         )),
    dict(name="Lekha Nilayam", role="Homeowner", organisation="Private residence",
         location="Hyderabad", project="lekha-nilayam", order=2,
         quote=(
             "We wanted the lift to sit in the middle of the house without closing it in. Zion "
             "designed the shaft around the light rather than the other way round."
         )),
    dict(name="Owaisi Hospitals", role="Facilities", organisation="Owaisi Hospitals",
         location="Santosh Nagar, Hyderabad", project="owaisi-hospitals", is_featured=True, order=3,
         quote=(
             "Our lifts move beds, not just people. Levelling and door width were the specifications "
             "we cared about, and those are the ones that were got right."
         )),
    dict(name="Kashi Yadhav", role="Homeowner", organisation="Private residence",
         location="Hyderabad", project="kashi-yadhav-residence", order=4,
         quote=(
             "The house was finished and we were living in it. They built the whole shaft in the "
             "stairwell without cutting a single slab."
         )),
    dict(name="Chath Restaurant", role="Management", organisation="Chath Restaurant",
         location="Hyderabad", project="chath-restaurant", order=5,
         quote=(
             "The rooftop only works as a dining floor because guests can reach it in seconds. The "
             "lift made that terrace commercially viable."
         )),
]

TEAM = [
    ("Engineering", "Design & engineering", "engineering", False,
     "Shaft surveys, general arrangement drawings, traffic analysis and system selection.",
     M.frame("kashi-shaft")),
    ("Manufacturing", "Fabrication & assembly", "manufacturing", False,
     "Car frames, cabins, structural shafts and finishing, built and load-tested in-house.",
     M.frame("kashi-structure")),
    ("Installation", "Site installation", "installation", False,
     "Rail alignment, machine setting, door adjustment and commissioning on site.",
     M.frame("kashi-machine")),
    ("Service", "Maintenance & 24/7 response", "installation", False,
     "Preventive maintenance, safety testing and the out-of-hours breakdown desk.",
     M.frame("kashi-drive")),
]

AWARDS = [
    ("Recognition for quality in vertical transportation", "Industry association", "2023",
     "Recognised for consistency of installation quality across residential and healthcare projects.",
     M.frame("lekha-cabin")),
    ("Excellence in customer service", "Regional business awards", "2022",
     "Recognised for the 24/7 after-sales operation and entrapment response record.",
     M.frame("lacheta-inuse")),
    ("ISO 9001 certification", "Independent certification body", "2019",
     "Quality management system certified across design, manufacture, installation and service.",
     M.frame("owaisi-cop")),
]

# --------------------------------------------------------------------- Gallery
GALLERY = [
    # (category, title, meta, media path, w, h, featured)
    ("interiors", "Brass and marble entrance", "Home Elevator · Private residence · Hyderabad", M.interior(1), 1536, 2752, True),
    ("interiors", "Lift lobby in a residential tower", "MRL Traction · Apartment building · Hyderabad", M.interior(2), 1536, 2752, False),
    ("interiors", "Double-height hall", "Home Elevator · Private residence · Hyderabad", M.interior(3), 1536, 2752, False),
    ("commercial", "Black-framed panoramic lift", "Capsule Elevator · Commercial · Hyderabad", M.interior(4), 1536, 2752, True),
    ("interiors", "Gearless passenger lift lobby", "MRL Traction · Apartment building", M.interior(5), 1536, 2752, False),
    ("commercial", "Retail lift entrance", "Passenger Elevator · Retail · Hyderabad", M.interior(6), 1536, 2752, False),
    ("interiors", "Timber-lined lift lobby", "Home Elevator · Private residence", M.interior(7), 1536, 2752, False),
    ("interiors", "Stone and steel lobby", "MRL Traction · Private residence", M.interior(8), 1536, 2752, False),
    ("interiors", "Bronze cabin against stone", "Home Elevator · Private residence", M.interior(9), 1536, 2752, False),
    ("interiors", "Hydraulic lift lobby", "Hydraulic Elevator · Private residence", M.interior(10), 1536, 2752, False),

    ("residential", "Lekha Nilayam from above", "Home Elevator · Private residence · Hyderabad", M.frame("lekha-aerial"), 3840, 2160, True),
    ("residential", "Glazed shaft in the hall", "Home Elevator · Lekha Nilayam", M.frame("lekha-hall"), 3840, 2160, False),
    ("residential", "Bronze car, Lekha Nilayam", "Home Elevator · Lekha Nilayam", M.frame("lekha-cabin"), 3840, 2160, False),
    ("residential", "Starlight ceiling", "Detail · Lekha Nilayam", M.frame("lekha-ceiling"), 3840, 2160, False),
    ("residential", "Antique brass lobby", "Home Elevator · Lacheta Nivas", M.frame("lacheta-lobby"), 2160, 3840, False),
    ("residential", "Cove-lit car ceiling", "Detail · Lacheta Nivas", M.frame("lacheta-ceiling"), 2160, 3840, False),
    ("residential", "Floor indicator", "Detail · Lacheta Nivas", M.frame("lacheta-indicator"), 2160, 3840, False),
    ("residential", "Capsule lift in the atrium", "Capsule Elevator · Chilkuru Residence", M.frame("chilkuru-atrium"), 2160, 3840, True),
    ("residential", "Rooftop pavilion", "Capsule Elevator · Chilkuru Residence", M.frame("chilkuru-pavilion"), 2160, 3840, False),
    ("residential", "Villa from above", "Capsule Elevator · Chilkuru Residence", M.frame("chilkuru-aerial"), 2160, 3379, False),

    ("commercial", "Chath Restaurant elevation", "Passenger Elevator · Hospitality · Hyderabad", M.frame("chath-facade"), 3840, 2160, True),
    ("commercial", "Rooftop dining terrace", "Passenger Elevator · Chath Restaurant", M.frame("chath-terrace"), 3840, 2160, False),
    ("commercial", "Landing indicators", "Detail · Chath Restaurant", M.frame("chath-indicator"), 3840, 2160, False),
    ("commercial", "Restaurant at night, from above", "Passenger Elevator · Chath Restaurant", M.frame("chath-aerial"), 3840, 1900, False),

    ("institutional", "Owaisi Hospitals lift lobby", "Hospital Elevator · Healthcare · Hyderabad", M.frame("owaisi-lobby"), 2160, 3379, True),
    ("institutional", "Stretcher-capable car", "Hospital Elevator · Owaisi Hospitals", M.frame("owaisi-cabin"), 2160, 3379, False),
    ("institutional", "Lift bank", "Hospital Elevator · Owaisi Hospitals", M.frame("owaisi-doors"), 2160, 3379, False),
    ("institutional", "Ward corridor", "Hospital Elevator · Owaisi Hospitals", M.frame("owaisi-corridor"), 2160, 3379, False),

    ("installation", "Self-supporting shaft structure", "Retrofit · Kashi Yadhav's Residence", M.frame("kashi-structure"), 2160, 3840, True),
    ("installation", "Gearless machine at the shaft head", "Retrofit · Kashi Yadhav's Residence", M.frame("kashi-drive"), 2160, 3840, False),
    ("installation", "Drive and sheave", "Retrofit · Kashi Yadhav's Residence", M.frame("kashi-machine"), 2160, 3840, False),
    ("installation", "Looking up the glazed shaft", "Retrofit · Kashi Yadhav's Residence", M.frame("kashi-shaft"), 2160, 3840, False),
]

def run():
    """Write the editorial content.

    The journal category table is gone, so the seed no longer creates it: the
    slug in each row is the value stored on the post itself.
    """
    now = timezone.now()
    for i, row in enumerate(JOURNAL, 1):
        row = dict(row)
        slug = row.pop("slug")
        row["hero_image_url"] = row.pop("hero", "")
        row["published_at"] = now - timedelta(days=row.pop("days_ago", 0))
        row["order"] = i
        BlogPost.objects.update_or_create(slug=slug, defaults=row)

    projects = {p.slug: p for p in Project.objects.all()}
    for row in TESTIMONIALS:
        row = dict(row)
        row["project"] = projects.get(row.pop("project", ""))
        row["video_url"] = row.pop("video", "")
        row["poster_url"] = row.pop("poster", "")
        Testimonial.objects.update_or_create(name=row["name"], defaults=row)

    for i, (name, role, dept, lead, bio, photo) in enumerate(TEAM, 1):
        TeamMember.objects.update_or_create(
            name=name, role=role,
            defaults=dict(department=dept, is_leadership=lead, bio=bio,
                          photo_url=photo, order=i),
        )

    for i, (name, org, year, desc, image) in enumerate(AWARDS, 1):
        Award.objects.update_or_create(
            name=name,
            defaults=dict(organisation=org, year=year, description=desc,
                          image_url=image, order=i),
        )

    GalleryItem.objects.all().delete()
    for i, (cat, title, meta, src, w, h, feat) in enumerate(GALLERY, 1):
        GalleryItem.objects.create(category=cat, title=title, meta=meta, image_url=src,
                                   width=w, height=h, is_featured=feat, order=i)

    return {
        "blog_posts": BlogPost.objects.count(),
        "testimonials": Testimonial.objects.count(),
        "team": TeamMember.objects.count(),
        "awards": Award.objects.count(),
        "gallery_items": GalleryItem.objects.count(),
    }
