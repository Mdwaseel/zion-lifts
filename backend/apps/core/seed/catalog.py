"""Catalogue seed: applications, safety tests, finishes, components, and the lift range.

Specifications follow ordinary Indian passenger-lift practice (EN 81 / IS 14665
families) and should be confirmed against Zion's own datasheets before launch.
"""

from apps.catalog.models import (
    Application,
    Component,
    FinishOption,
    LiftImage,
    LiftSpec,
    LiftType,
    LiftVariant,
    SafetyFeature,
)

from . import media as M

APPLICATIONS = [
    ("villa", "Villas & private homes", "residential",
     "Two to five levels, tight shafts, finishes chosen to match the interior."),
    ("apartment", "Apartment buildings", "residential",
     "Daily-duty passenger lifts sized for family traffic and stretcher access."),
    ("hotel", "Hotels & hospitality", "commercial",
     "Guest lifts, service lifts and dumbwaiters running to different schedules."),
    ("office", "Offices & retail", "commercial",
     "Peak-hour traffic, group control, and finishes that survive heavy use."),
    ("hospital", "Hospitals & clinics", "institutional",
     "Stretcher-width lifts, levelling accuracy, and dependable emergency behaviour."),
    ("institutional", "Government & education", "institutional",
     "Tendered specifications, accessibility compliance, long service life."),
    ("industrial", "Factories & warehouses", "industrial",
     "Goods handling, heavy loads, robust lifts built for daily abuse."),
    ("parking", "Parking & basements", "industrial",
     "Stacking and moving vehicles where floor area is the constraint."),
]

SAFETY = [
    ("overload", "Overload detection", "The lift will not move if it is asked to carry too much.",
     "Load cells under the lift platform measure weight continuously. Past the rated load the "
     "doors stay open, an audible warning sounds and the lift holds at the landing until weight "
     "is removed.",
     "The lift is loaded past 110% of rated capacity; departure must be inhibited.",
     "IS 14665 / EN 81-20"),
    ("power-failure", "Automatic rescue device", "A power cut moves you to the nearest floor, not nowhere.",
     "On mains failure the ARD battery takes over, drives the lift at reduced speed to the "
     "nearest landing, opens the doors and holds the cabin light and fan on.",
     "Mains supply is cut mid-travel; the lift must land and release passengers unaided.",
     "IS 14665 Part 4"),
    ("emergency-braking", "Overspeed governor & safety gear", "If the lift ever runs fast, steel jaws close on the rails.",
     "An overspeed governor senses descent above the trip speed and mechanically engages "
     "progressive safety gear, which grips the guide rails and brings the lift to a controlled stop.",
     "The governor is tripped at rated overspeed with the lift loaded; the safety gear must set "
     "and hold on the rails.",
     "EN 81-20 / EN 81-50"),
    ("fire-mode", "Firefighter recall", "In an alarm the lift stops being a lift and becomes an exit route.",
     "On a fire signal the lift cancels all calls, returns to the designated evacuation landing, "
     "parks with doors open and locks out normal operation until reset.",
     "The fire input is asserted; the lift must recall and park without accepting further calls.",
     "IS 14665 / NBC 2016"),
    ("seismic", "Structural & seismic restraint", "Rails, brackets and counterweights are tied to the structure.",
     "Guide rails, brackets and counterweight frames are designed and fixed for the seismic zone "
     "of the site, with retaining plates that keep the counterweight in its guides.",
     "Bracket spacing and fixings are verified against the shaft structure and site seismic zone.",
     "IS 1893 / EN 81-77"),
    ("door-protection", "Door light curtain", "The doors see you before they touch you.",
     "A full-height infrared curtain across the entrance re-opens the doors on any obstruction, "
     "with no contact required.",
     "The curtain is broken at multiple heights while closing; doors must reverse each time.",
     "EN 81-20"),
    ("emergency-comms", "Alarm & two-way intercom", "Someone answers, day or night.",
     "The alarm button connects to a battery-backed intercom that reaches Zion's 24/7 service "
     "desk, independent of the building's power.",
     "The alarm is pressed with mains isolated; a voice link must be established.",
     "EN 81-28"),
]

FINISHES = [
    # wall material
    ("material", "brushed-steel", "Brushed stainless steel", "Hairline 304 stainless — the default for daily-duty lifts.", "#B9BEC2", "#8E959A", "standard", 1),
    ("material", "antique-brass", "Antique brass", "Warm brushed brass, as used at Lacheta Nivas.", "#B08D57", "#8A6B3B", "premium", 2),
    ("material", "rose-gold", "Rose gold mirror", "Mirror-polished titanium coating with a rose cast.", "#C08A70", "#9C6A52", "premium", 3),
    ("material", "walnut", "Walnut veneer", "Book-matched veneer panels in a steel frame.", "#6B4A33", "#4A3121", "premium", 4),
    ("material", "stone-grey", "Stone laminate", "Marble-effect laminate for high-traffic buildings.", "#C7C2B8", "#A29C90", "standard", 5),
    ("material", "obsidian", "Black mirror", "Mirror-polished black stainless with a fine etch.", "#1B1E21", "#0B0B0B", "premium", 6),
    # flooring
    ("floor", "granite", "Granite", "Sealed granite slab, matched to the lobby.", "#6E6A66", "#4C4945", "premium", 1),
    ("floor", "marble", "Marble", "Statuario-type marble with a honed finish.", "#E4E1DA", "#C4BFB4", "premium", 2),
    ("floor", "vinyl", "Commercial vinyl", "Slip-resistant sheet vinyl for hospitals and offices.", "#8E959A", "#6B7276", "standard", 3),
    ("floor", "chequer", "Steel chequer plate", "Anti-slip plate for goods and service lifts.", "#7D8286", "#5A5F63", "standard", 4),
    # lighting
    ("light", "cove", "Perimeter cove", "Indirect LED cove around a floating ceiling.", "#F2E4C8", "#D8C49A", "premium", 1),
    ("light", "spots", "Recessed spots", "Discreet warm-white downlights in a flat ceiling.", "#F4EFE4", "#D9D2C2", "standard", 2),
    ("light", "starlight", "Starlight ceiling", "Dense fibre-point ceiling, as at Lekha Nilayam.", "#FFF3D6", "#E8D5A6", "signature", 3),
    ("light", "linear", "Linear channels", "Continuous LED channels running the length of the lift.", "#EFF3F5", "#CBD3D8", "standard", 4),
    # doors
    ("door", "centre-auto", "Centre-opening automatic", "Two panels parting from the centre — the quietest option.", "#B9BEC2", "#8E959A", "standard", 1),
    ("door", "side-auto", "Side-opening automatic", "Telescopic panels to one side, for narrow shafts.", "#ADB3B7", "#868C90", "standard", 2),
    ("door", "glass-auto", "Glass automatic", "Toughened glass panels in a metal frame.", "#CBDDE0", "#9FB8BD", "premium", 3),
    ("door", "manual-swing", "Manual swing + collapsible", "Economical landing doors for low-traffic homes.", "#9AA0A5", "#73797D", "standard", 4),
    # control panel
    ("control", "brushed-cop", "Brushed steel COP", "Full-height panel with micro-movement buttons.", "#B9BEC2", "#8E959A", "standard", 1),
    ("control", "touch-cop", "Capacitive touch COP", "Flush glass panel with backlit floor markings.", "#25292C", "#0F1113", "premium", 2),
    ("control", "braille-cop", "Braille & audio COP", "Tactile markings and voice announcement, accessibility-ready.", "#A8AEB2", "#7E858A", "standard", 3),
    # handrail
    ("handrail", "round-steel", "Round steel handrail", "32 mm brushed steel on three sides.", "#B9BEC2", "#8E959A", "standard", 1),
    ("handrail", "flat-brass", "Flat brass handrail", "Rectangular brass rail on the rear wall.", "#B08D57", "#8A6B3B", "premium", 2),
]

COMPONENTS = [
    ("traction-machine", "01", "Traction machine",
     "A gearless permanent-magnet motor sits at the head of the shaft and drives the sheave "
     "directly. No gearbox means no gear oil, less heat and markedly less noise.",
     "Gearless PMSM · integrated brake", "Drive"),
    ("guide-rails", "02", "Guide rails & brackets",
     "Machined steel T-rails hold the cabin and counterweight on a single vertical plane for the "
     "whole travel. Everything else in the shaft is aligned to them.",
     "T-profile rails on bracketed fixings", "Structure"),
    ("safety-gear", "03", "Safety gear & governor",
     "An overspeed governor watches the lift's descent. If it ever exceeds the trip speed, "
     "progressive safety gear grips the rails and stops the lift mechanically.",
     "Progressive safety gear · overspeed governor", "Safety"),
    ("controller", "04", "Control system",
     "A VVVF drive shapes every start and stop, so acceleration is a curve rather than a step. "
     "Floor levelling lands within a few millimetres, loaded or empty.",
     "Closed-loop VVVF · serial cabin communication", "Control"),
    ("door-operator", "05", "Door operator",
     "The doors are the part passengers touch most. A dedicated VVVF operator drives them, "
     "with a full-height light curtain that reopens on any obstruction.",
     "VVVF door drive · infrared curtain", "Doors"),
    ("counterweight", "06", "Counterweight",
     "Cast filler weights balance the cabin plus roughly half its rated load, so the motor only "
     "ever moves the difference.",
     "Cabin weight + 50% of rated load", "Structure"),
    ("suspension", "07", "Suspension ropes",
     "Multiple independent steel ropes carry the cabin, each rated well beyond the whole load. "
     "They are inspected and re-tensioned at every service.",
     "Steel wire ropes · redundant reeving", "Suspension"),
    ("buffers", "08", "Pit buffers",
     "At the bottom of the shaft, buffers absorb the energy of an over-travel so nothing "
     "reaches the pit floor at speed.",
     "Polyurethane or oil buffers, by speed", "Safety"),
]

# slug, name, eyebrow, tagline, summary, overview, specs..., media
LIFTS = [
    dict(
        slug="home-elevator", name="Home Elevator", short_name="Home",
        eyebrow="Residential", accent="#B08D57", order=1, is_featured=True,
        tagline="A lift that belongs to the house, not to the building services.",
        summary=(
            "Compact, quiet and finished to match the interior around it. Designed for villas and "
            "private residences of two to five levels, where the shaft has to fit the architecture "
            "rather than the other way round."
        ),
        overview=(
            "A home lift is judged on different terms to a commercial one. It runs a handful of "
            "trips a day, so raw throughput matters less than how it sounds at night, how it looks "
            "from the living room, and how little of the plan it consumes. Zion builds home "
            "elevators around a compact machine-room-less drive, so the only space you give up is "
            "the shaft itself.\n\n"
            "Finishes are chosen with the interior, not from a fixed catalogue — brass, walnut, "
            "stone, mirror steel and glass all work within the same cabin shell. Where there is no "
            "existing shaft, a self-supporting steel structure with glazed infill can be built "
            "inside a stairwell or against an external wall."
        ),
        speed="0.3 – 1.0 m/s", capacity="272 – 408 kg (4 – 6 persons)",
        stops="2 – 6 stops", drive="Machine-room-less gearless traction",
        min_floors=2, max_floors=6, min_persons=3, max_persons=6,
        pit_depth="From 350 mm", headroom="From 2,600 mm",
        shaft_footprint="From 1,100 × 1,000 mm", machine_room="Not required",
        hero=M.frame("lacheta-lobby"),
        hero_video=M.video("lacheta-nivas", loop=True),
        apps=["villa", "apartment"],
        safety=["overload", "power-failure", "emergency-braking", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.frame("lacheta-glass"), "Glazed home lift beside the stair"),
            ("cabin", M.frame("lacheta-ceiling"), "Cabin ceiling and cove lighting"),
            ("detail", M.frame("lacheta-indicator"), "Floor indicator"),
            ("gallery", M.interior(1), "Brass and marble entrance lobby"),
            ("gallery", M.interior(3), "Home lift in a double-height hall"),
            ("gallery", M.interior(7), "Timber-lined lift lobby"),
            ("gallery", M.interior(9), "Bronze cabin against stone"),
            ("detail", M.frame("lacheta-cop"), "Lift operating panel"),
        ],
        variants=[
            ("ZH-4", "Compact 4-passenger", "The smallest practical shaft for a private home.",
             "272 kg", "4 persons", "0.3 m/s", "1,100 × 1,000 mm"),
            ("ZH-5", "Standard 5-passenger", "The usual choice for a three- to four-level villa.",
             "340 kg", "5 persons", "0.5 m/s", "1,250 × 1,100 mm"),
            ("ZH-6", "Wide 6-passenger", "Extra width where a wheelchair must turn inside the lift.",
             "408 kg", "6 persons", "0.5 m/s", "1,400 × 1,200 mm"),
        ],
        specs=[
            ("Dimensions", "Minimum shaft", "1,100 × 1,000 mm", "Internal, plumb over full travel"),
            ("Dimensions", "Pit depth", "350 – 600 mm", "Reduced-pit arrangement available"),
            ("Dimensions", "Headroom", "2,600 mm", "Above the top finished floor level"),
            ("Dimensions", "Clear door opening", "700 – 900 mm", ""),
            ("Power", "Supply", "3-phase 415 V or 1-phase 230 V", "Depending on drive"),
            ("Power", "Standby draw", "Under 100 W", "With cabin lighting on standby"),
            ("Performance", "Rated speed", "0.3 – 1.0 m/s", ""),
            ("Performance", "Levelling accuracy", "± 5 mm", "Loaded or empty"),
            ("Performance", "Noise in lift", "Under 55 dB(A)", "At rated speed"),
        ],
    ),
    dict(
        slug="capsule-elevator", name="Capsule Elevator", short_name="Capsule",
        eyebrow="Panoramic", accent="#048D8E", order=2, is_featured=True,
        tagline="A lift you look out of, and a building looks into.",
        summary=(
            "A glazed observation cabin in a glazed shaft, used where the lift is part of the "
            "architecture — atriums, hotel lobbies, retail floors and double-height homes."
        ),
        overview=(
            "A capsule lift stops being building services and becomes a piece of the room. The cabin "
            "is glazed on two, three or all four sides, the shaft is a structural glass and steel "
            "assembly, and everything that would normally be hidden — the rails, the ropes, the "
            "lift frame — is detailed on the assumption it will be seen.\n\n"
            "That changes how it is built. Structure is designed for the sightline as much as the "
            "load, cabling is routed inside the frame, and glass is toughened and laminated so a "
            "failure stays in place. The result is a lift that carries people and also carries "
            "the middle of the room."
        ),
        speed="0.5 – 1.5 m/s", capacity="408 – 1,020 kg (6 – 15 persons)",
        stops="2 – 12 stops", drive="Gearless traction, MRL or overhead",
        min_floors=2, max_floors=12, min_persons=6, max_persons=15,
        pit_depth="From 900 mm", headroom="From 3,600 mm",
        shaft_footprint="From 1,600 × 1,600 mm", machine_room="Not required",
        hero=M.product("capsule", 2),
        apps=["hotel", "office", "villa", "apartment"],
        safety=["overload", "power-failure", "emergency-braking", "fire-mode", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.product("capsule", 1), "Capsule lift in a residential atrium"),
            ("gallery", M.product("capsule", 3), "Capsule lift in a retail atrium"),
            ("gallery", M.product("capsule", 4), "Panoramic lift in a hotel lobby"),
            ("gallery", M.frame("chilkuru-capsule"), "Glazed capsule at Chilkuru Residence"),
            ("gallery", M.frame("chilkuru-atrium"), "Capsule shaft through the atrium"),
            ("detail", M.frame("kashi-shaft"), "Structural glass shaft, seen from below"),
            ("gallery", M.interior(4), "Black-framed panoramic lift"),
        ],
        variants=[
            ("ZC-6", "Semi-panoramic 6-passenger", "Glazed on one face, solid on three.",
             "408 kg", "6 persons", "0.5 m/s", "1,600 × 1,600 mm"),
            ("ZC-8", "Three-sided 8-passenger", "The usual atrium configuration.",
             "544 kg", "8 persons", "1.0 m/s", "1,800 × 1,700 mm"),
            ("ZC-13", "Full panoramic 13-passenger", "Glazed on all four faces for a free-standing shaft.",
             "884 kg", "13 persons", "1.5 m/s", "2,100 × 1,900 mm"),
        ],
        specs=[
            ("Dimensions", "Minimum shaft", "1,600 × 1,600 mm", "Structural glass shaft"),
            ("Dimensions", "Pit depth", "900 – 1,400 mm", "By speed"),
            ("Dimensions", "Headroom", "3,600 mm", ""),
            ("Glazing", "Lift glazing", "Toughened laminated, 10 – 13.5 mm", "Interlayer retains on failure"),
            ("Glazing", "Shaft glazing", "Toughened laminated in a steel frame", ""),
            ("Performance", "Rated speed", "0.5 – 1.5 m/s", ""),
            ("Performance", "Levelling accuracy", "± 5 mm", ""),
        ],
    ),
    dict(
        slug="mrl-traction", name="MRL Traction Elevator", short_name="MRL",
        eyebrow="Machine-room-less", accent="#8B8B86", order=3, is_featured=True,
        tagline="The whole machine lives in the shaft.",
        summary=(
            "A gearless permanent-magnet drive mounted at the head of the shaft, removing the "
            "machine room entirely. The efficient default for most new buildings."
        ),
        overview=(
            "Machine-room-less traction is the modern default, and for good reason. A compact "
            "gearless motor mounts on the guide rails at the top of the shaft, so the building "
            "gains back the room that used to sit above it, and the drive loses the gearbox that "
            "used to generate most of its noise and all of its oil changes.\n\n"
            "A closed-loop VVVF drive shapes acceleration and deceleration into a curve, holds "
            "levelling within a few millimetres regardless of load, and regenerates on the "
            "descent. For a mid-rise building this is the quietest, most efficient and lowest-"
            "maintenance arrangement Zion builds."
        ),
        speed="1.0 – 2.5 m/s", capacity="408 – 1,600 kg (6 – 24 persons)",
        stops="2 – 20 stops", drive="Gearless PMSM, machine-room-less",
        min_floors=2, max_floors=20, min_persons=6, max_persons=24,
        pit_depth="From 1,200 mm", headroom="From 3,800 mm",
        shaft_footprint="From 1,700 × 1,800 mm", machine_room="Not required",
        hero=M.interior(5),
        apps=["apartment", "office", "hotel", "institutional"],
        safety=["overload", "power-failure", "emergency-braking", "fire-mode", "seismic", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.interior(8), "MRL passenger lift lobby"),
            ("detail", M.frame("kashi-drive"), "Gearless machine at the shaft head"),
            ("detail", M.frame("kashi-machine"), "Drive and sheave assembly"),
            ("detail", M.frame("kashi-structure"), "Lift frame and guide rails"),
            ("gallery", M.interior(2), "Lift lobby in a residential tower"),
        ],
        variants=[
            ("ZM-8", "8-passenger", "Small residential or boutique office core.",
             "544 kg", "8 persons", "1.0 m/s", "1,700 × 1,800 mm"),
            ("ZM-13", "13-passenger", "The standard apartment and office lift.",
             "884 kg", "13 persons", "1.5 m/s", "1,900 × 2,000 mm"),
            ("ZM-20", "20-passenger", "High-traffic cores and stretcher-capable lobbies.",
             "1,360 kg", "20 persons", "2.0 m/s", "2,100 × 2,300 mm"),
        ],
        specs=[
            ("Dimensions", "Minimum shaft", "1,700 × 1,800 mm", "For an 8-passenger lift"),
            ("Dimensions", "Pit depth", "1,200 – 1,600 mm", "By rated speed"),
            ("Dimensions", "Headroom", "3,800 – 4,400 mm", "By rated speed"),
            ("Power", "Supply", "3-phase 415 V, 50 Hz", ""),
            ("Power", "Regeneration", "Available", "Returns braking energy to the building supply"),
            ("Performance", "Rated speed", "1.0 – 2.5 m/s", ""),
            ("Performance", "Levelling accuracy", "± 3 mm", ""),
            ("Performance", "Noise in lift", "Under 52 dB(A)", ""),
        ],
    ),
    dict(
        slug="hydraulic-elevator", name="Hydraulic Elevator", short_name="Hydraulic",
        eyebrow="Low-rise", accent="#C7C2B8", order=4,
        tagline="Load carried by the floor, not by the roof.",
        summary=(
            "A jack pushes the lift from below, so the shaft carries almost no load and the "
            "structure above it can stay light. Well suited to retrofits and heavy low-rise duty."
        ),
        overview=(
            "In a hydraulic lift the cabin sits on a ram driven by an oil power pack, so the "
            "building does not need to support the whole suspended load at the top of the shaft. "
            "That makes it the natural answer when a lift is being added to a building that was "
            "never designed for one, or when the load is heavy and the travel is short.\n\n"
            "The power unit can be sited away from the shaft, in a cupboard on the lowest level, "
            "which is often the only place a retrofit has room for. Travel is limited and speed is "
            "modest, but within those limits it is a forgiving, serviceable and quiet machine."
        ),
        speed="0.15 – 0.63 m/s", capacity="408 – 2,000 kg",
        stops="2 – 6 stops", drive="Hydraulic jack with submersible power pack",
        min_floors=2, max_floors=6, min_persons=4, max_persons=20,
        pit_depth="From 900 mm", headroom="From 3,400 mm",
        shaft_footprint="From 1,500 × 1,600 mm", machine_room="Compact remote cabinet",
        hero=M.interior(10),
        apps=["villa", "apartment", "office", "industrial"],
        safety=["overload", "power-failure", "emergency-braking", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.interior(2), "Hydraulic passenger lift lobby"),
            ("gallery", M.interior(6), "Retrofit lift in an existing stairwell"),
            ("detail", M.frame("kashi-structure"), "Lift frame and rails"),
        ],
        variants=[
            ("ZY-6", "6-passenger direct-acting", "Single ram under the lift, for two or three levels.",
             "408 kg", "6 persons", "0.3 m/s", "1,500 × 1,600 mm"),
            ("ZY-13", "13-passenger indirect", "Roped 2:1 ram for greater travel.",
             "884 kg", "13 persons", "0.63 m/s", "1,900 × 2,000 mm"),
            ("ZY-GOODS", "Goods duty", "Heavy platform for short-travel goods handling.",
             "2,000 kg", "—", "0.25 m/s", "2,200 × 2,600 mm"),
        ],
        specs=[
            ("Dimensions", "Maximum travel", "Up to 18 m", "Practical limit for direct-acting"),
            ("Dimensions", "Pit depth", "900 – 1,200 mm", ""),
            ("Dimensions", "Headroom", "3,400 mm", "Lower than traction for the same lift"),
            ("Plant", "Power unit", "Submersible pump in an oil tank", "Sited remotely, up to 10 m away"),
            ("Plant", "Oil temperature", "Monitored, with cooling option", ""),
            ("Performance", "Rated speed", "0.15 – 0.63 m/s", ""),
            ("Performance", "Levelling accuracy", "± 5 mm", "Re-levelling on load change"),
        ],
    ),
    dict(
        slug="passenger-elevator", name="Commercial Passenger Elevator", short_name="Passenger",
        eyebrow="Commercial", accent="#048D8E", order=5, is_featured=True,
        tagline="Built for the eight-forty-five rush.",
        summary=(
            "High-duty passenger lifts for offices, hotels and retail, with group control across "
            "two or more lifts and finishes chosen to survive constant use."
        ),
        overview=(
            "A commercial lift is specified around its worst five minutes, not its average hour. "
            "Zion sizes lifts, speeds and door timings against the building's expected peak "
            "handling capacity, and where more than one lift serves the same floors, a group "
            "controller allocates calls between them so passengers wait once rather than twice.\n\n"
            "Everything a passenger touches is chosen for wear: hairline stainless walls that do "
            "not show handprints the way mirror does, micro-movement buttons rated for millions of "
            "operations, and flooring that can be replaced in a night without taking the lift apart."
        ),
        speed="1.0 – 2.5 m/s", capacity="544 – 1,600 kg (8 – 24 persons)",
        stops="2 – 20 stops", drive="Gearless traction with group control",
        min_floors=3, max_floors=20, min_persons=8, max_persons=24,
        pit_depth="From 1,400 mm", headroom="From 4,000 mm",
        shaft_footprint="From 1,900 × 2,000 mm", machine_room="Not required",
        hero=M.frame("chath-entrance"),
        hero_video=M.video("chath-restaurant", loop=True),
        apps=["office", "hotel", "institutional", "apartment"],
        safety=["overload", "power-failure", "emergency-braking", "fire-mode", "seismic", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.frame("chath-cabin"), "Passenger lift at Chath Restaurant"),
            ("gallery", M.frame("chath-facade"), "Lift within the building facade"),
            ("detail", M.frame("chath-indicator"), "Landing indicators"),
            ("detail", M.frame("chath-ceiling"), "Lift ceiling and lighting"),
            ("gallery", M.interior(4), "Commercial lift lobby"),
            ("gallery", M.interior(6), "Retail lift entrance"),
        ],
        variants=[
            ("ZP-8", "8-passenger", "Boutique offices and small hotels.",
             "544 kg", "8 persons", "1.0 m/s", "1,900 × 2,000 mm"),
            ("ZP-13", "13-passenger", "The standard commercial lift.",
             "884 kg", "13 persons", "1.5 m/s", "2,000 × 2,100 mm"),
            ("ZP-20", "20-passenger", "Main lobby duty in a busy building.",
             "1,360 kg", "20 persons", "2.5 m/s", "2,100 × 2,400 mm"),
        ],
        specs=[
            ("Dimensions", "Minimum shaft", "1,900 × 2,000 mm", ""),
            ("Dimensions", "Clear door opening", "900 – 1,200 mm", ""),
            ("Control", "Group control", "Up to 8 lifts", "Duplex, triplex and group collective"),
            ("Control", "Dispatch", "Full collective selective", ""),
            ("Performance", "Rated speed", "1.0 – 2.5 m/s", ""),
            ("Performance", "Door open time", "0.9 – 1.5 s", "Adjustable by traffic profile"),
            ("Performance", "Levelling accuracy", "± 3 mm", ""),
        ],
    ),
    dict(
        slug="hospital-elevator", name="Hospital Elevator", short_name="Hospital",
        eyebrow="Healthcare", accent="#048D8E", order=6,
        tagline="Wide enough for a trolley, gentle enough for the patient on it.",
        summary=(
            "Deep stretcher-capable lifts with accurate levelling, wide clear openings and "
            "wipe-clean surfaces, built for hospitals, nursing homes and diagnostic centres."
        ),
        overview=(
            "A hospital lift is dimensioned by the trolley, not the passenger count. The cabin is "
            "deep rather than wide so a bed, its attendants and an IV stand fit without turning, "
            "and the clear opening is sized to let all of that through in one movement.\n\n"
            "Ride quality matters more here than anywhere else. Acceleration is shaped gently, "
            "levelling is held tight so a trolley wheel does not catch on the sill, and the whole "
            "cabin interior is specified in surfaces that can be cleaned down between uses. Zion has "
            "delivered this configuration at Owaisi Hospitals in Hyderabad."
        ),
        speed="0.5 – 1.75 m/s", capacity="1,020 – 2,040 kg (15 – 30 persons)",
        stops="2 – 15 stops", drive="Gearless traction, MRL or overhead",
        min_floors=2, max_floors=15, min_persons=15, max_persons=30,
        pit_depth="From 1,500 mm", headroom="From 4,200 mm",
        shaft_footprint="From 2,200 × 2,900 mm", machine_room="Optional",
        hero=M.frame("owaisi-doors"),
        hero_video=M.video("owaisi-hospitals", loop=True),
        apps=["hospital", "institutional"],
        safety=["overload", "power-failure", "emergency-braking", "fire-mode", "seismic", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.frame("owaisi-lobby"), "Lift lobby at Owaisi Hospitals"),
            ("cabin", M.frame("owaisi-cabin"), "Stretcher-capable lift"),
            ("detail", M.frame("owaisi-cop"), "Lift operating panel"),
            ("detail", M.frame("owaisi-ceiling"), "Lift ceiling and lighting"),
            ("gallery", M.frame("owaisi-waiting"), "Waiting area at the lift bank"),
            ("gallery", M.frame("owaisi-corridor"), "Ward corridor entrance"),
            ("gallery", M.frame("owaisi-exterior"), "Owaisi Hospitals, Santosh Nagar"),
        ],
        variants=[
            ("ZS-15", "15-passenger stretcher", "Single-trolley lift for clinics and nursing homes.",
             "1,020 kg", "15 persons", "1.0 m/s", "2,200 × 2,900 mm"),
            ("ZS-20", "20-passenger bed lift", "Bed plus attendants and equipment.",
             "1,360 kg", "20 persons", "1.5 m/s", "2,400 × 3,000 mm"),
            ("ZS-26", "26-passenger", "Main clinical circulation core.",
             "1,768 kg", "26 persons", "1.75 m/s", "2,600 × 3,100 mm"),
        ],
        specs=[
            ("Dimensions", "Lift internal", "1,500 × 2,400 mm typical", "Depth sized to the trolley"),
            ("Dimensions", "Clear door opening", "1,200 – 1,400 mm", ""),
            ("Dimensions", "Pit depth", "1,500 – 1,800 mm", ""),
            ("Interior", "Surfaces", "Hairline stainless, wipe-clean", "No open joints at floor level"),
            ("Interior", "Handrails", "Three sides", ""),
            ("Performance", "Levelling accuracy", "± 3 mm", "Critical for trolley wheels"),
            ("Performance", "Ride", "Shaped acceleration", "Jerk limited for patient comfort"),
        ],
    ),
    dict(
        slug="goods-elevator", name="Goods & Freight Elevator", short_name="Goods",
        eyebrow="Industrial", accent="#8B8B86", order=7,
        tagline="Built to be loaded badly and keep working.",
        summary=(
            "Heavy-duty platforms and lifts for factories, warehouses and service cores, with "
            "chequer-plate floors, protected walls and openings sized around a pallet."
        ),
        overview=(
            "A goods lift spends its life being loaded off-centre by someone in a hurry. It is "
            "built accordingly: a stiffer lift frame, chequer-plate flooring, bump rails on the "
            "walls, and a door arrangement that clears a full pallet or trolley in one pass.\n\n"
            "Duty is specified around the heaviest single item rather than an average, and the "
            "drive is geared for controlled low-speed handling rather than travel time. Where "
            "vehicles or very heavy point loads are involved, a hydraulic platform is usually the "
            "more robust answer than a traction lift."
        ),
        speed="0.25 – 1.0 m/s", capacity="500 – 5,000 kg",
        stops="2 – 10 stops", drive="Geared traction or hydraulic platform",
        min_floors=2, max_floors=10, min_persons=4, max_persons=20,
        pit_depth="From 1,200 mm", headroom="From 3,800 mm",
        shaft_footprint="From 1,800 × 2,000 mm", machine_room="Optional",
        hero=M.frame("kashi-structure"),
        apps=["industrial", "office", "hotel"],
        safety=["overload", "power-failure", "emergency-braking", "fire-mode", "door-protection", "emergency-comms"],
        images=[
            ("gallery", M.frame("kashi-machine"), "Drive and structural frame"),
            ("detail", M.frame("kashi-drive"), "Traction machine"),
        ],
        variants=[
            ("ZG-500", "500 kg service lift", "Kitchen, stores and light service duty.",
             "500 kg", "—", "0.25 m/s", "1,400 × 1,600 mm"),
            ("ZG-1500", "1,500 kg goods lift", "Pallet handling between production floors.",
             "1,500 kg", "20 persons", "0.5 m/s", "2,000 × 2,600 mm"),
            ("ZG-5000", "5,000 kg heavy platform", "Machinery and vehicle-adjacent loads.",
             "5,000 kg", "—", "0.25 m/s", "3,000 × 4,500 mm"),
        ],
        specs=[
            ("Dimensions", "Platform", "Sized to the load, up to 3,000 × 4,500 mm", ""),
            ("Dimensions", "Clear opening", "Full platform width where required", ""),
            ("Lift", "Flooring", "Steel chequer plate", "Or sealed industrial screed"),
            ("Lift", "Wall protection", "Bump rails and kick plates", ""),
            ("Doors", "Type", "Vertical bi-parting or horizontal sliding", ""),
            ("Performance", "Rated speed", "0.25 – 1.0 m/s", "Low speed favours controlled handling"),
        ],
    ),
    dict(
        slug="dumbwaiter", name="Dumbwaiter", short_name="Dumbwaiter",
        eyebrow="Service", accent="#B9BEC2", order=8,
        tagline="The shortest distance between the kitchen and the table.",
        summary=(
            "A small service lift for food, linen, files and stores. Stainless throughout, sized "
            "to a worktop, and quiet enough to sit inside a dining room wall."
        ),
        overview=(
            "A dumbwaiter removes the single most tiring movement in a restaurant or a large "
            "house: carrying trays up stairs. The lift is stainless steel inside and out, the "
            "landing openings sit at counter height so nothing has to be lifted, and the whole "
            "assembly is compact enough to build into a wall cavity.\n\n"
            "Because it never carries people, the safety case is simpler and the shaft can be far "
            "smaller — but the door interlocks, overload cut-out and emergency stop all work the "
            "same way they do on a passenger lift."
        ),
        speed="0.3 – 0.5 m/s", capacity="50 – 300 kg",
        stops="2 – 6 stops", drive="Drum or traction, machine-room-less",
        min_floors=2, max_floors=6, min_persons=0, max_persons=0,
        pit_depth="Not required (floor-level option)", headroom="From 1,200 mm above top landing",
        shaft_footprint="From 600 × 600 mm", machine_room="Not required",
        hero=M.product("dumbwaiter", 2),
        apps=["hotel", "villa", "office"],
        safety=["overload", "door-protection", "power-failure"],
        images=[
            ("gallery", M.product("dumbwaiter", 1), "Counter-height dumbwaiter in a kitchen"),
            ("gallery", M.product("dumbwaiter", 3), "Service hatch in a restaurant"),
            ("gallery", M.product("dumbwaiter", 4), "Dumbwaiter loading in a hotel kitchen"),
        ],
        variants=[
            ("ZD-50", "50 kg table-top", "Documents, trays and light stores.",
             "50 kg", "—", "0.3 m/s", "600 × 600 mm"),
            ("ZD-100", "100 kg counter-height", "The standard restaurant configuration.",
             "100 kg", "—", "0.4 m/s", "800 × 800 mm"),
            ("ZD-300", "300 kg floor-level", "Trolley-in service lift for hotels.",
             "300 kg", "—", "0.5 m/s", "1,000 × 1,000 mm"),
        ],
        specs=[
            ("Dimensions", "Lift internal", "500 × 500 mm up to 1,000 × 1,000 mm", ""),
            ("Dimensions", "Landing height", "Counter level or floor level", ""),
            ("Lift", "Material", "304 stainless steel throughout", "Shelves removable for cleaning"),
            ("Doors", "Type", "Vertical bi-parting stainless", "Interlocked at every landing"),
            ("Safety", "Occupancy", "Goods only", "Lift size prevents human entry"),
        ],
    ),
    dict(
        slug="car-stacker", name="Car Stacker & Parking Lift", short_name="Car Stacker",
        eyebrow="Parking", accent="#8B8B86", order=9,
        tagline="Two, three or four cars in one car's footprint.",
        summary=(
            "Mechanical parking systems that stack vehicles vertically — puzzle, pit and stack "
            "arrangements for homes, offices and basements where floor area has run out."
        ),
        overview=(
            "Parking is the one building problem that only goes upward. A stacker lifts one "
            "vehicle above another on a steel platform, doubling or trebling capacity within the "
            "same slab. Simple two-post stackers suit a private driveway; puzzle systems shuffle "
            "platforms horizontally as well as vertically for a full basement.\n\n"
            "The engineering is different from a passenger lift — hydraulic or chain-driven "
            "platforms, mechanical locking pawls that hold the load independently of the "
            "hydraulics, and a control interface designed for a driver rather than a passenger."
        ),
        speed="0.05 – 0.15 m/s", capacity="2,000 – 2,700 kg per platform",
        stops="2 – 4 levels", drive="Hydraulic or chain-driven platform",
        min_floors=2, max_floors=4, min_persons=0, max_persons=0,
        pit_depth="0 – 2,100 mm", headroom="From 3,600 mm",
        shaft_footprint="From 2,700 × 5,600 mm per bay", machine_room="Compact power pack",
        hero=M.product("car-stacker", 2),
        apps=["parking", "industrial", "office", "villa"],
        safety=["overload", "power-failure", "emergency-braking"],
        images=[
            ("gallery", M.product("car-stacker", 1), "Two-level stacker at a private residence"),
            ("gallery", M.product("car-stacker", 3), "Multi-bay stacker in a commercial forecourt"),
            ("gallery", M.product("car-stacker", 4), "Covered stacker in a basement"),
            ("gallery", M.product("car-stacker", 5), "Street-level parking stacker"),
        ],
        variants=[
            ("ZK-2", "Two-level stacker", "One platform over one ground space.",
             "2,300 kg", "—", "0.1 m/s", "2,700 × 5,600 mm"),
            ("ZK-3", "Three-level pit stacker", "Two platforms over a pit space.",
             "2,300 kg", "—", "0.1 m/s", "2,700 × 5,600 mm"),
            ("ZK-P", "Puzzle system", "Platforms move sideways as well as up, for dense basements.",
             "2,700 kg", "—", "0.05 m/s", "By layout"),
        ],
        specs=[
            ("Dimensions", "Platform", "2,300 × 5,300 mm usable", "Sedan and SUV variants"),
            ("Dimensions", "Vehicle height", "1,550 – 2,050 mm", "By configuration"),
            ("Load", "Per platform", "2,000 – 2,700 kg", ""),
            ("Safety", "Mechanical locking", "Pawls hold the platform independently of hydraulics", ""),
            ("Safety", "Perimeter", "Photocell and physical guards", ""),
            ("Control", "Operation", "Key-switch or remote, hold-to-run", ""),
        ],
    ),
]


def run():
    apps_by_slug = {}
    for slug, name, group, desc in APPLICATIONS:
        obj, _ = Application.objects.update_or_create(
            slug=slug,
            defaults=dict(name=name, group=group, description=desc,
                          order=APPLICATIONS.index((slug, name, group, desc)) + 1),
        )
        apps_by_slug[slug] = obj

    safety_by_slug = {}
    for i, (slug, name, headline, desc, test, standard) in enumerate(SAFETY, 1):
        obj, _ = SafetyFeature.objects.update_or_create(
            slug=slug,
            defaults=dict(name=name, headline=headline, description=desc,
                          test_procedure=test, standard=standard, order=i),
        )
        safety_by_slug[slug] = obj

    for cat, slug, name, desc, hex1, hex2, tier, order in FINISHES:
        FinishOption.objects.update_or_create(
            category=cat, slug=slug,
            defaults=dict(name=name, description=desc, swatch_hex=hex1,
                          swatch_hex_2=hex2, tier=tier, order=order),
        )

    for i, (slug, index, name, desc, detail, supplier) in enumerate(COMPONENTS, 1):
        Component.objects.update_or_create(
            slug=slug,
            defaults=dict(index=index, name=name, description=desc,
                          detail=detail, supplier=supplier, order=i),
        )

    for row in LIFTS:
        row = dict(row)
        app_slugs = row.pop("apps", [])
        safety_slugs = row.pop("safety", [])
        images = row.pop("images", [])
        variants = row.pop("variants", [])
        specs = row.pop("specs", [])
        row["hero_image_url"] = row.pop("hero", "")
        row["hero_video_url"] = row.pop("hero_video", "")
        slug = row.pop("slug")

        lift, _ = LiftType.objects.update_or_create(slug=slug, defaults=row)
        lift.applications.set([apps_by_slug[s] for s in app_slugs if s in apps_by_slug])
        lift.safety_features.set([safety_by_slug[s] for s in safety_slugs if s in safety_by_slug])

        lift.images.all().delete()
        for i, (kind, url, alt) in enumerate(images, 1):
            LiftImage.objects.create(lift_type=lift, kind=kind, image_url=url,
                                     alt=alt, caption=alt, order=i)
        lift.variants.all().delete()
        for i, (code, name, desc, cap, persons, speed, shaft) in enumerate(variants, 1):
            LiftVariant.objects.create(lift_type=lift, code=code, name=name, description=desc,
                                       capacity=cap, persons=persons, speed=speed,
                                       shaft=shaft, order=i)
        lift.specs.all().delete()
        for i, (group, label, value, note) in enumerate(specs, 1):
            LiftSpec.objects.create(lift_type=lift, group=group, label=label,
                                    value=value, note=note, order=i)

    return {
        "applications": Application.objects.count(),
        "safety_features": SafetyFeature.objects.count(),
        "finishes": FinishOption.objects.count(),
        "components": Component.objects.count(),
        "lift_types": LiftType.objects.count(),
        "variants": LiftVariant.objects.count(),
        "specs": LiftSpec.objects.count(),
    }
