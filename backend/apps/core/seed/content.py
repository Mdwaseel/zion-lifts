"""Editorial seed: FAQ, journal, testimonials, timeline, service, gallery, legal."""

from datetime import date, timedelta

from django.utils import timezone

from apps.content.models import (
    FAQ,
    Award,
    FAQCategory,
    GalleryItem,
    JournalCategory,
    JournalPost,
    LegalClause,
    LegalDocument,
    Milestone,
    ServicePillar,
    TeamMember,
    Testimonial,
)
from apps.projects.models import Project

from . import media as M

# ------------------------------------------------------------------------- FAQ
FAQ_DATA = [
    ("choosing-a-lift", "Choosing a lift", "Sizing, type and where to start.", [
        ("Which type of lift do I need for a private house?",
         "For most villas of two to five levels, a machine-room-less home elevator is the right "
         "answer: it needs no plant room, fits a shaft from about 1,100 × 1,000 mm, and runs quietly "
         "enough to sit next to bedrooms. If the lift is going into an atrium or a double-height "
         "hall where it will be seen, a glazed capsule lift is worth the extra shaft.",
         "Explore Home Elevators", "/lifts/home-elevator", "general"),
        ("How much space does a lift actually need?",
         "Less than most people assume. A compact four-passenger home lift needs an internal shaft "
         "from roughly 1,100 × 1,000 mm, a pit from 350 mm and about 2,600 mm of headroom above the "
         "top floor. A commercial eight-passenger car needs about 1,900 × 2,000 mm. Send us a floor "
         "plan and we will mark up what fits.",
         "See dimensions by lift type", "/lifts", "general"),
        ("What if my building has no lift shaft at all?",
         "A self-supporting steel structure can be erected inside a stairwell void or against an "
         "external wall, carrying its own loads to a new pad at the base. We did exactly this at "
         "Kashi Yadhav's Residence — a four-storey occupied house that never had a shaft.",
         "See that project", "/projects/kashi-yadhav-residence", "general"),
        ("How many people should the lift carry?",
         "Size by the worst case, not the average. For a home, count the largest group that will "
         "realistically travel together — and if anyone may need a wheelchair, specify a car deep "
         "enough to turn in. For a commercial building, size against expected peak five-minute "
         "traffic rather than headcount.", "", "", "general"),
        ("Traction or hydraulic — which is better?",
         "Traction for almost everything: quieter, more efficient, better ride, more travel. "
         "Hydraulic earns its place on short travels where the structure cannot carry suspended "
         "load at the top of the shaft, or where a very heavy load moves a short distance.",
         "Compare the systems", "/lifts", "general"),
        ("Can the lift match my interior?",
         "Yes — that is usually the point. Wall material, flooring, ceiling, lighting, handrail and "
         "control panel are all specified separately. At Lacheta Nivas the car was detailed with the "
         "joinery, in antique brass with a marble floor.",
         "Build a configuration", "/lifts/home-elevator", "general"),
        ("Do you work outside Hyderabad?",
         "Yes. Hyderabad and the wider Telangana region are our core service area, and we take "
         "projects across South India where we can commit to the same installation and maintenance "
         "response. Tell us the location and we will say honestly whether we can support it.",
         "", "", "general"),
        ("How long does a lift last?",
         "A well-maintained passenger lift runs for 20 to 25 years before it needs modernisation, "
         "and modernisation usually means new drive, controller and interior on the existing shaft "
         "and rails rather than a full replacement.",
         "Ask about modernisation", "/contact", "general"),
    ]),
    ("products-technology", "Products & technology", "Drives, controls and how the machine works.", [
        ("What does machine-room-less actually mean?",
         "The traction machine mounts on the guide rails at the head of the shaft instead of in a "
         "room above it. The building gets that room back, and because the motor is gearless there "
         "is no gearbox, no gear oil and much less noise.",
         "See the MRL system", "/lifts/mrl-traction", "general"),
        ("Why is a gearless motor better than a geared one?",
         "A gearless permanent-magnet motor drives the sheave directly. Removing the gearbox removes "
         "the main source of mechanical noise, the main heat load, and the oil changes. It is also "
         "more efficient, and with a regenerative drive it returns braking energy to the building.",
         "", "", "general"),
        ("What is a VVVF drive?",
         "Variable-voltage variable-frequency control. It shapes the motor's speed continuously, so "
         "starting and stopping follow a curve rather than a step. That is what makes a modern lift "
         "feel smooth, and it is what holds floor levelling within a few millimetres whether the car "
         "is full or empty.", "", "", "general"),
        ("How accurate is floor levelling?",
         "Within ±3 mm on our traction systems and ±5 mm on hydraulic, loaded or empty. That "
         "matters most in hospitals, where a trolley wheel will find any lip at the sill.",
         "See hospital lifts", "/lifts/hospital-elevator", "general"),
        ("How noisy is a lift inside the house?",
         "A gearless MRL home lift runs under about 55 dB(A) inside the car at rated speed — "
         "conversation level. Most of what people remember as lift noise came from geared machines "
         "and relay controllers, neither of which we fit.", "", "", "general"),
        ("Can I get a lift with a glass shaft?",
         "Yes. Both the structural shaft and the car can be glazed, in toughened laminated glass so "
         "any failure stays in place. This is how the capsule lifts at Chilkuru Residence and Lekha "
         "Nilayam are built.",
         "Explore Capsule Elevators", "/lifts/capsule-elevator", "general"),
    ]),
    ("installation", "Installation", "Survey, programme and what happens on site.", [
        ("How long does an installation take?",
         "For a home lift with a ready shaft, typically three to five weeks on site after delivery. "
         "A retrofit that needs its own structure runs longer, and a commercial group of several "
         "cars is programmed floor by floor. We give you a dated programme before we start.",
         "", "", "general"),
        ("What do you need from me before you can quote?",
         "A floor plan and a section if you have them, the number of levels, the floor-to-floor "
         "heights, and what the lift is for. If there is an existing shaft, its internal dimensions "
         "and pit depth. Drawings can be uploaded with your enquiry.",
         "Start an enquiry", "/contact", "general"),
        ("Do you do a site survey?",
         "Always, before anything is manufactured. Shafts are rarely plumb and rarely the dimension "
         "on the drawing. The survey is where we find that out, not the installation.", "", "", "general"),
        ("Who prepares the shaft?",
         "Civil work — the shaft walls, the pit, waterproofing and the power supply to the "
         "controller position — is usually by the builder, to a drawing we issue. We can take on the "
         "structural shaft itself where there is none.", "", "", "general"),
        ("Can a lift be installed in an occupied building?",
         "Yes, and most of our retrofits are. Work is sequenced to keep the stair usable, and the "
         "noisy operations are programmed rather than sprung on the household.",
         "See a retrofit", "/projects/kashi-yadhav-residence", "general"),
        ("What power supply does a lift need?",
         "Usually a three-phase 415 V supply to the controller position, sized to the drive. Some "
         "compact home lifts run on single-phase 230 V. We confirm the requirement at survey so the "
         "electrician can allow for it.", "", "", "general"),
        ("What happens at handover?",
         "Load testing to 125% of rated capacity, an overspeed and safety-gear trip test, levelling "
         "and door timing adjustment, statutory inspection paperwork, and a walkthrough with whoever "
         "will operate the building.", "", "", "general"),
    ]),
    ("safety", "Safety", "What protects you, and how it is proven.", [
        ("What happens in a power cut?",
         "The automatic rescue device takes over on battery, drives the car at reduced speed to the "
         "nearest landing, opens the doors and keeps the cabin light and fan running. You are not "
         "waiting in the dark for the mains to return.", "", "", "general"),
        ("What stops the lift falling?",
         "Nothing about a lift depends on one component. The car hangs on multiple independent steel "
         "ropes, each rated well beyond the whole load. Above that, an overspeed governor watches "
         "the descent, and if the car ever exceeds the trip speed, progressive safety gear grips the "
         "guide rails mechanically and stops it.", "", "", "general"),
        ("Can the doors close on someone?",
         "A full-height infrared curtain across the entrance reopens the doors on any obstruction, "
         "with no contact needed. It sees a hand, a bag strap or a walking stick.", "", "", "general"),
        ("What happens if there is a fire?",
         "On a fire signal the car cancels all calls, returns to the designated evacuation landing, "
         "parks with its doors open and locks out normal operation until it is reset by the "
         "fire service.", "", "", "general"),
        ("Is the lift tested before I get it?",
         "Every car is load-tested to 125% of rated capacity and the overspeed governor and safety "
         "gear are tripped and verified before dispatch. The tests are then repeated on site after "
         "installation.", "", "", "general"),
        ("What if someone is trapped?",
         "Press the alarm. It connects to a battery-backed two-way intercom that reaches our service "
         "desk directly, independent of the building's power, 24 hours a day.",
         "Request service", "/contact", "general"),
    ]),
    ("maintenance", "Maintenance & service", "After the doors open.", [
        ("What does an AMC cover?",
         "Scheduled preventive visits, adjustment, lubrication, rope and brake inspection, safety "
         "testing, and priority breakdown response. Comprehensive contracts include parts; "
         "non-comprehensive ones bill parts separately.",
         "Talk about an AMC", "/contact", "general"),
        ("How often should a lift be serviced?",
         "Monthly for commercial and healthcare installations, quarterly at minimum for a home lift. "
         "Frequency is set by usage, not by the calendar alone.", "", "", "general"),
        ("How fast do you respond to a breakdown?",
         "Our service desk is staffed 24/7 and we prioritise entrapments above everything else. "
         "Response times to site are set out in your maintenance contract.",
         "Get service support", "/contact", "general"),
        ("Do you service lifts you did not install?",
         "Yes, subject to a survey. We need to see the equipment and its history before we can take "
         "responsibility for it, and we will tell you honestly if something needs putting right "
         "before a contract starts.", "", "", "general"),
        ("Can an old lift be modernised instead of replaced?",
         "Usually. Drive, controller, doors and interior can be replaced on the existing shaft, "
         "rails and structure — better ride and efficiency for a fraction of the disruption of a "
         "full replacement.",
         "Discuss modernisation", "/contact", "general"),
        ("Are spare parts available years later?",
         "We hold parts for the systems we install and support them through their service life. "
         "This is one of the reasons we keep the range deliberately narrow.", "", "", "general"),
    ]),
    ("pricing-enquiry", "Pricing & enquiry", "Cost, quotes and what happens next.", [
        ("How much does a lift cost?",
         "Honestly, it depends on travel, capacity, drive type and finish, and the range is wide "
         "enough that any single number quoted here would mislead you. Send the floors and the "
         "building type and we will come back with a real figure rather than a bracket.",
         "Get a quote", "/contact", "general"),
        ("What drives the cost most?",
         "Number of stops first, then capacity, then finish. Going from a standard stainless car to "
         "a brass or stone interior changes the price meaningfully; adding a floor changes it more.",
         "", "", "general"),
        ("Is installation included in the quote?",
         "Yes. Our quotes cover supply, installation and commissioning, and state clearly what is "
         "excluded — usually civil work, the power supply to the controller and any statutory fees.",
         "", "", "general"),
        ("How long is a quote valid?",
         "Typically 30 days, because steel and component pricing moves. The validity is stated on "
         "the quotation itself.", "", "", "general"),
        ("What happens after I submit an enquiry?",
         "We review the drawings and the brief, call you to fill in what the form could not, "
         "recommend a system with reasons, and then quote against that recommendation.",
         "", "", "general"),
        # contact-scoped
        ("How quickly will someone get back to me?",
         "Within one working day for project enquiries. Service and breakdown calls are answered "
         "24/7 on the service line.", "", "", "contact"),
        ("Can I upload drawings with my enquiry?",
         "Yes — PDF, JPG, PNG, WEBP, DWG and DXF, up to six files of 10 MB each. Plans and sections "
         "are the two most useful things you can send.", "", "", "contact"),
        ("I have an existing lift, not a new project.",
         "Use the service route rather than the project enquiry form. It reaches our service desk "
         "directly instead of the sales pipeline.", "", "", "contact"),
        ("Can I visit the factory?",
         "Yes, by appointment. Seeing cars being fabricated and load-tested tells you more about a "
         "lift company than any brochure.", "", "", "contact"),
        ("Do you do site visits before quoting?",
         "For anything beyond a straightforward new-build shaft, yes. It is the only reliable way "
         "to quote a retrofit.", "", "", "contact"),
    ]),
]

# --------------------------------------------------------------------- Journal
JOURNAL_CATEGORIES = [
    ("elevators", "Elevators"), ("architecture", "Architecture"),
    ("engineering", "Engineering"), ("safety", "Safety"),
    ("maintenance", "Maintenance"), ("projects", "Projects"),
]

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

# -------------------------------------------------------------------- The story
MILESTONES = [
    ("2012", "Zion Lifts is founded",
     "Started in Hyderabad with a small workshop, a handful of engineers and a straightforward "
     "purpose: to help people move better, safer and more comfortably.", M.frame("kashi-floor")),
    ("2014", "First manufacturing unit",
     "Fabrication is brought in-house so car frames, cabins and structural shafts are built to "
     "Zion's own tolerances rather than bought in.", M.frame("owaisi-doors")),
    ("2016", "Commercial and institutional work",
     "The range widens beyond homes into offices, hotels and healthcare, which brings group "
     "control, stretcher cars and heavier duty cycles with it.", M.frame("owaisi-lobby")),
    ("2018", "24/7 service desk",
     "A dedicated after-sales operation is established, with an out-of-hours line and an "
     "entrapment-first response policy.", M.frame("chilkuru-panel")),
    ("2020", "Gearless MRL becomes the standard",
     "Machine-room-less gearless traction is adopted as the default across the passenger range, "
     "for quieter, more efficient and lower-maintenance installations.", M.frame("kashi-drive")),
    ("2022", "Glass and capsule programme",
     "Structural glazed shafts and panoramic cars become a distinct line of work as architects "
     "start treating the lift as part of the room.", M.frame("chilkuru-atrium")),
    ("2024", "1,750+ installations",
     "Zion passes 1,750 installations across residential, commercial, hospitality, healthcare and "
     "industrial buildings, with a team of 95–100 people.", M.frame("lekha-cabin")),
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

SERVICE_PILLARS = [
    ("service-24-7", "24/7 breakdown support", "wrench",
     "A staffed service desk every hour of the year, with entrapments prioritised above all other calls.",
     "Answered by a person, not a queue."),
    ("amc", "Annual maintenance contracts", "calendar",
     "Scheduled preventive visits covering ropes, brakes, doors, levelling, the pit and the intercom, "
     "with safety testing recorded.",
     "Comprehensive and non-comprehensive options."),
    ("breakdown", "Breakdown response", "bolt",
     "Priority attendance under contracted response times, with the parts we hold for the systems we install.",
     "Response times stated in the contract."),
    ("modernisation", "Modernisation", "refresh",
     "New drive, controller, doors and interior on the existing shaft and rails — better ride and "
     "efficiency without a full replacement.",
     "Typically at 20–25 years."),
    ("spares", "Spare parts", "box",
     "Parts held and supported through the service life of every system we install.",
     "Deliberately narrow range, deeply supported."),
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

# ----------------------------------------------------------------------- Legal
LEGAL = [
    dict(slug="privacy", title="Privacy Policy",
         intro="How Zion Lifts collects, uses and protects the information you give us.",
         clauses=[
             ("Who we are",
              "Zion Lifts Pvt. Ltd. is a lift manufacturer and installer based in Hyderabad, "
              "Telangana, India. In this policy, 'we' and 'us' mean Zion Lifts Pvt. Ltd. If you "
              "have any question about this policy, write to info@zionlifts.com."),
             ("What we collect",
              "When you submit a project enquiry or service request we collect your name, phone "
              "number, email address, organisation if given, the details of your building and "
              "requirement, any message you write, and any drawings you upload. Our website also "
              "records ordinary technical information such as the pages requested and the browser "
              "used, for security and to understand which pages are useful."),
             ("Why we use it",
              "To respond to your enquiry, prepare a quotation, arrange a site survey, deliver and "
              "maintain equipment, and keep records of the work we have done. We use your contact "
              "details to contact you about the enquiry you made. We do not sell your information, "
              "and we do not use it for unrelated marketing without asking you first."),
             ("Drawings and attachments",
              "Files you upload with an enquiry are stored so our engineers can review them. They "
              "are treated as confidential to your project, shared only with the Zion staff working "
              "on it, and retained with the enquiry record."),
             ("Who we share it with",
              "Only where necessary: our own staff, and service providers who host our systems or "
              "carry our email, under obligations of confidentiality. We also disclose information "
              "where the law requires it. We do not share your details with third parties for their "
              "own marketing."),
             ("How long we keep it",
              "Enquiries that do not proceed are retained for up to three years so we can pick up a "
              "conversation you resume. Records relating to equipment we have supplied are kept for "
              "the service life of that equipment and as long afterwards as our legal and warranty "
              "obligations require."),
             ("How we protect it",
              "Access to enquiry records is restricted to staff who need it. Data is transmitted "
              "over encrypted connections and held on access-controlled systems. No system is "
              "perfectly secure, but we take the protection of your information seriously."),
             ("Your choices",
              "You may ask us for a copy of the information we hold about you, ask us to correct "
              "anything inaccurate, or ask us to delete information we no longer need to keep. "
              "Write to info@zionlifts.com and we will respond within a reasonable period."),
         ]),
    dict(slug="terms", title="Terms of Use",
         intro="The terms on which this website is made available.",
         clauses=[
             ("Acceptance", "By using this website you accept these terms. If you do not accept "
              "them, please do not use the site."),
             ("About the information here",
              "This website describes the products and services Zion Lifts offers. It is provided "
              "for general information and does not by itself constitute a contractual offer."),
             ("Specifications are indicative",
              "Dimensions, capacities, speeds, drive types and other technical figures shown on "
              "this site are typical values for the configurations described. The specification "
              "for any particular installation is established by survey and confirmed in writing in "
              "the quotation and order documents, which take precedence over anything on this site."),
             ("Quotations and orders",
              "Prices are given only in a written quotation, are valid for the period stated on it, "
              "and are subject to survey. A contract is formed only when an order is accepted by "
              "us in writing."),
             ("Enquiries you submit",
              "You confirm that the information you submit is accurate and that you are entitled to "
              "share any drawings you upload. Do not upload material you do not have the right to "
              "share with us."),
             ("Intellectual property",
              "The content of this site, including text, photographs, films, drawings, the Zion "
              "Lifts name and the Zion Lifts mark, belongs to Zion Lifts or its licensors. You may "
              "view and print pages for your own reference. You may not reproduce or republish them "
              "commercially without our written permission. Third-party images used on this site "
              "are credited separately and remain subject to their own licences."),
             ("Third-party links",
              "Where we link to another website, we do so for convenience. We are not responsible "
              "for the content of sites we do not operate."),
             ("Availability",
              "We try to keep this site available and correct, but we do not guarantee that it will "
              "be uninterrupted or free of error, and we may change or withdraw content at any time."),
             ("Liability",
              "Nothing in these terms excludes liability that cannot lawfully be excluded, "
              "including for death or personal injury caused by negligence, or for fraud. Subject "
              "to that, we are not liable for indirect or consequential loss arising from use of "
              "this website."),
             ("Governing law",
              "These terms are governed by the laws of India, and the courts at Hyderabad, "
              "Telangana have exclusive jurisdiction."),
         ]),
    dict(slug="cookies", title="Cookie Policy",
         intro="What this site stores in your browser, and why.",
         clauses=[
             ("What cookies are",
              "Cookies are small files a website asks your browser to store. Related technologies "
              "such as local storage work in a similar way. This policy covers both."),
             ("What we use",
              "This site is deliberately light on tracking. We use strictly necessary storage to "
              "keep the site working — for example remembering a form step you have reached or a "
              "preference such as reduced motion — and, where enabled, aggregate analytics to "
              "understand which pages are used."),
             ("Strictly necessary storage",
              "Needed for the site to function, including security protection on the enquiry forms. "
              "These cannot be switched off through the site because the site would not work "
              "correctly without them."),
             ("Analytics",
              "Where analytics is enabled, it tells us which pages are visited and how people move "
              "through the site, in aggregate. We use it to decide what to improve, not to identify "
              "individual visitors."),
             ("Third-party content",
              "Pages that embed a map from Google Maps will load content from Google, which may set "
              "its own cookies under Google's policies. We do not control those cookies."),
             ("Managing cookies",
              "Every major browser lets you see the cookies a site has set, delete them, and block "
              "future ones. Blocking strictly necessary cookies may stop parts of this site, "
              "particularly the enquiry forms, from working."),
             ("Changes",
              "If we add anything that stores more than is described here, we will update this "
              "policy and the effective date shown above it."),
         ]),
]


def run():
    for ci, (cslug, cname, cdesc, questions) in enumerate(FAQ_DATA, 1):
        cat, _ = FAQCategory.objects.update_or_create(
            slug=cslug, defaults=dict(name=cname, description=cdesc, order=ci)
        )
        cat.questions.all().delete()
        for qi, (q, a, label, url, scope) in enumerate(questions, 1):
            FAQ.objects.create(category=cat, question=q, answer=a, link_label=label,
                               link_url=url, scope=scope, order=qi)

    jcats = {}
    for i, (slug, name) in enumerate(JOURNAL_CATEGORIES, 1):
        obj, _ = JournalCategory.objects.update_or_create(
            slug=slug, defaults=dict(name=name, order=i)
        )
        jcats[slug] = obj

    now = timezone.now()
    for i, row in enumerate(JOURNAL, 1):
        row = dict(row)
        slug = row.pop("slug")
        row["category"] = jcats[row.pop("category")]
        row["hero_image_url"] = row.pop("hero", "")
        row["published_at"] = now - timedelta(days=row.pop("days_ago", 0))
        row["order"] = i
        JournalPost.objects.update_or_create(slug=slug, defaults=row)

    projects = {p.slug: p for p in Project.objects.all()}
    for row in TESTIMONIALS:
        row = dict(row)
        row["project"] = projects.get(row.pop("project", ""))
        row["video_url"] = row.pop("video", "")
        row["poster_url"] = row.pop("poster", "")
        Testimonial.objects.update_or_create(name=row["name"], defaults=row)

    for i, (year, title, desc, image) in enumerate(MILESTONES, 1):
        Milestone.objects.update_or_create(
            year=year, title=title,
            defaults=dict(description=desc, image_url=image, order=i),
        )

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

    for i, (slug, name, icon, desc, detail) in enumerate(SERVICE_PILLARS, 1):
        ServicePillar.objects.update_or_create(
            slug=slug,
            defaults=dict(name=name, icon=icon, description=desc, detail=detail, order=i),
        )

    GalleryItem.objects.all().delete()
    for i, (cat, title, meta, src, w, h, feat) in enumerate(GALLERY, 1):
        GalleryItem.objects.create(category=cat, title=title, meta=meta, image_url=src,
                                   width=w, height=h, is_featured=feat, order=i)

    for doc in LEGAL:
        obj, _ = LegalDocument.objects.update_or_create(
            slug=doc["slug"],
            defaults=dict(title=doc["title"], intro=doc["intro"],
                          effective_date=date(2026, 1, 1)),
        )
        obj.clauses.all().delete()
        for i, (heading, body) in enumerate(doc["clauses"], 1):
            LegalClause.objects.create(document=obj, heading=heading, body=body, order=i)

    return {
        "faq_categories": FAQCategory.objects.count(),
        "faqs": FAQ.objects.count(),
        "journal_posts": JournalPost.objects.count(),
        "testimonials": Testimonial.objects.count(),
        "milestones": Milestone.objects.count(),
        "team": TeamMember.objects.count(),
        "awards": Award.objects.count(),
        "service_pillars": ServicePillar.objects.count(),
        "gallery_items": GalleryItem.objects.count(),
        "legal_documents": LegalDocument.objects.count(),
    }
