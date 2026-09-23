/**
 * Every question we answer, grouped by what the reader is trying to decide.
 *
 * The shape is the one `/api/faq-categories/` used to return — a category with
 * its questions nested — because that is what /faq renders and what /lifts and
 * /lifts/:slug pull a single section out of.
 *
 * `scope` is 'general' unless a question only makes sense on the contact page
 * ("how quickly will someone get back to me?"). `faqCategories('contact')`
 * narrows to those, and the counts narrow with it: a chip reading 9 above a
 * list of 2 is a bug, not a rounding difference.
 *
 * `link_url` is an in-app route, so it must stay a path the router knows. An
 * answer that sends someone to a 404 is worse than one that ends at the
 * full stop.
 */

const FAQ_CATEGORIES = [
  {
    id: 'choosing-a-lift',
    slug: 'choosing-a-lift',
    name: 'Choosing a lift',
    description: 'Sizing, type and where to start.',
    questions: [
      {
        id: 'which-type-private-house',
        question: 'Which type of lift do I need for a private house?',
        answer:
          'For most villas of two to five levels, a machine-room-less home elevator is the right ' +
          'answer: it needs no plant room, fits a shaft from about 1,100 × 1,000 mm, and runs ' +
          'quietly enough to sit next to bedrooms. If the lift is going into an atrium or a ' +
          'double-height hall where it will be seen, a glazed capsule lift is worth the extra shaft.',
        link_label: 'Explore Home Elevators',
        link_url: '/lifts/home-elevator',
        scope: 'general',
      },
      {
        id: 'how-much-space',
        question: 'How much space does a lift actually need?',
        answer:
          'Less than most people assume. A compact four-passenger home lift needs an internal ' +
          'shaft from roughly 1,100 × 1,000 mm, a pit from 350 mm and about 2,600 mm of headroom ' +
          'above the top floor. A commercial eight-passenger car needs about 1,900 × 2,000 mm. ' +
          'Send us a floor plan and we will mark up what fits.',
        link_label: 'See dimensions by lift type',
        link_url: '/lifts',
        scope: 'general',
      },
      {
        id: 'no-shaft',
        question: 'What if my building has no lift shaft at all?',
        answer:
          'A self-supporting steel structure can be erected inside a stairwell void or against an ' +
          'external wall, carrying its own loads to a new pad at the base. We did exactly this at ' +
          "Kashi Yadhav's Residence — a four-storey occupied house that never had a shaft.",
        link_label: 'See that project',
        link_url: '/projects/kashi-yadhav-residence',
        scope: 'general',
      },
      {
        id: 'how-many-people',
        question: 'How many people should the lift carry?',
        answer:
          'Size by the worst case, not the average. For a home, count the largest group that will ' +
          'realistically travel together — and if anyone may need a wheelchair, specify a car deep ' +
          'enough to turn in. For a commercial building, size against expected peak five-minute ' +
          'traffic rather than headcount.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'traction-or-hydraulic',
        question: 'Traction or hydraulic — which is better?',
        answer:
          'Traction for almost everything: quieter, more efficient, better ride, more travel. ' +
          'Hydraulic earns its place on short travels where the structure cannot carry suspended ' +
          'load at the top of the shaft, or where a very heavy load moves a short distance.',
        link_label: 'Compare the systems',
        link_url: '/lifts',
        scope: 'general',
      },
      {
        id: 'match-my-interior',
        question: 'Can the lift match my interior?',
        answer:
          'Yes — that is usually the point. Wall material, flooring, ceiling, lighting, handrail ' +
          'and control panel are all specified separately. At Lacheta Nivas the car was detailed ' +
          'with the joinery, in antique brass with a marble floor.',
        link_label: 'Build a configuration',
        link_url: '/lifts/home-elevator',
        scope: 'general',
      },
      {
        id: 'outside-hyderabad',
        question: 'Do you work outside Hyderabad?',
        answer:
          'Yes. Hyderabad and the wider Telangana region are our core service area, and we take ' +
          'projects across South India where we can commit to the same installation and ' +
          'maintenance response. Tell us the location and we will say honestly whether we can ' +
          'support it.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'how-long-does-a-lift-last',
        question: 'How long does a lift last?',
        answer:
          'A well-maintained passenger lift runs for 20 to 25 years before it needs ' +
          'modernisation, and modernisation usually means new drive, controller and interior on ' +
          'the existing shaft and rails rather than a full replacement.',
        link_label: 'Ask about modernisation',
        link_url: '/contact',
        scope: 'general',
      },
    ],
  },
  {
    id: 'products-technology',
    slug: 'products-technology',
    name: 'Products & technology',
    description: 'Drives, controls and how the machine works.',
    questions: [
      {
        id: 'what-is-mrl',
        question: 'What does machine-room-less actually mean?',
        answer:
          'The traction machine mounts on the guide rails at the head of the shaft instead of in ' +
          'a room above it. The building gets that room back, and because the motor is gearless ' +
          'there is no gearbox, no gear oil and much less noise.',
        link_label: 'See the MRL system',
        link_url: '/lifts/mrl-traction',
        scope: 'general',
      },
      {
        id: 'gearless-vs-geared',
        question: 'Why is a gearless motor better than a geared one?',
        answer:
          'A gearless permanent-magnet motor drives the sheave directly. Removing the gearbox ' +
          'removes the main source of mechanical noise, the main heat load, and the oil changes. ' +
          'It is also more efficient, and with a regenerative drive it returns braking energy to ' +
          'the building.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'what-is-vvvf',
        question: 'What is a VVVF drive?',
        answer:
          'Variable-voltage variable-frequency control. It shapes the motor’s speed continuously, ' +
          'so starting and stopping follow a curve rather than a step. That is what makes a modern ' +
          'lift feel smooth, and it is what holds floor levelling within a few millimetres whether ' +
          'the car is full or empty.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'levelling-accuracy',
        question: 'How accurate is floor levelling?',
        answer:
          'Within ±3 mm on our traction systems and ±5 mm on hydraulic, loaded or empty. That ' +
          'matters most in hospitals, where a trolley wheel will find any lip at the sill.',
        link_label: 'See hospital lifts',
        link_url: '/lifts/hospital-elevator',
        scope: 'general',
      },
      {
        id: 'how-noisy',
        question: 'How noisy is a lift inside the house?',
        answer:
          'A gearless MRL home lift runs under about 55 dB(A) inside the car at rated speed — ' +
          'conversation level. Most of what people remember as lift noise came from geared ' +
          'machines and relay controllers, neither of which we fit.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'glass-shaft',
        question: 'Can I get a lift with a glass shaft?',
        answer:
          'Yes. Both the structural shaft and the car can be glazed, in toughened laminated glass ' +
          'so any failure stays in place. This is how the capsule lifts at Chilkuru Residence and ' +
          'Lekha Nilayam are built.',
        link_label: 'Explore Capsule Elevators',
        link_url: '/lifts/capsule-elevator',
        scope: 'general',
      },
    ],
  },
  {
    id: 'installation',
    slug: 'installation',
    name: 'Installation',
    description: 'Survey, programme and what happens on site.',
    questions: [
      {
        id: 'how-long-installation',
        question: 'How long does an installation take?',
        answer:
          'For a home lift with a ready shaft, typically three to five weeks on site after ' +
          'delivery. A retrofit that needs its own structure runs longer, and a commercial group ' +
          'of several cars is programmed floor by floor. We give you a dated programme before we ' +
          'start.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'what-you-need-to-quote',
        question: 'What do you need from me before you can quote?',
        answer:
          'A floor plan and a section if you have them, the number of levels, the floor-to-floor ' +
          'heights, and what the lift is for. If there is an existing shaft, its internal ' +
          'dimensions and pit depth. Drawings can be uploaded with your enquiry.',
        link_label: 'Start an enquiry',
        link_url: '/contact',
        scope: 'general',
      },
      {
        id: 'site-survey',
        question: 'Do you do a site survey?',
        answer:
          'Always, before anything is manufactured. Shafts are rarely plumb and rarely the ' +
          'dimension on the drawing. The survey is where we find that out, not the installation.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'who-prepares-shaft',
        question: 'Who prepares the shaft?',
        answer:
          'Civil work — the shaft walls, the pit, waterproofing and the power supply to the ' +
          'controller position — is usually by the builder, to a drawing we issue. We can take on ' +
          'the structural shaft itself where there is none.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'occupied-building',
        question: 'Can a lift be installed in an occupied building?',
        answer:
          'Yes, and most of our retrofits are. Work is sequenced to keep the stair usable, and the ' +
          'noisy operations are programmed rather than sprung on the household.',
        link_label: 'See a retrofit',
        link_url: '/projects/kashi-yadhav-residence',
        scope: 'general',
      },
      {
        id: 'power-supply',
        question: 'What power supply does a lift need?',
        answer:
          'Usually a three-phase 415 V supply to the controller position, sized to the drive. Some ' +
          'compact home lifts run on single-phase 230 V. We confirm the requirement at survey so ' +
          'the electrician can allow for it.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'handover',
        question: 'What happens at handover?',
        answer:
          'Load testing to 125% of rated capacity, an overspeed and safety-gear trip test, ' +
          'levelling and door timing adjustment, statutory inspection paperwork, and a walkthrough ' +
          'with whoever will operate the building.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
    ],
  },
  {
    id: 'safety',
    slug: 'safety',
    name: 'Safety',
    description: 'What protects you, and how it is proven.',
    questions: [
      {
        id: 'power-cut',
        question: 'What happens in a power cut?',
        answer:
          'The automatic rescue device takes over on battery, drives the car at reduced speed to ' +
          'the nearest landing, opens the doors and keeps the cabin light and fan running. You are ' +
          'not waiting in the dark for the mains to return.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'what-stops-a-fall',
        question: 'What stops the lift falling?',
        answer:
          'Nothing about a lift depends on one component. The car hangs on multiple independent ' +
          'steel ropes, each rated well beyond the whole load. Above that, an overspeed governor ' +
          'watches the descent, and if the car ever exceeds the trip speed, progressive safety ' +
          'gear grips the guide rails mechanically and stops it.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'doors-closing',
        question: 'Can the doors close on someone?',
        answer:
          'A full-height infrared curtain across the entrance reopens the doors on any ' +
          'obstruction, with no contact needed. It sees a hand, a bag strap or a walking stick.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'fire',
        question: 'What happens if there is a fire?',
        answer:
          'On a fire signal the car cancels all calls, returns to the designated evacuation ' +
          'landing, parks with its doors open and locks out normal operation until it is reset by ' +
          'the fire service.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'tested-before-dispatch',
        question: 'Is the lift tested before I get it?',
        answer:
          'Every car is load-tested to 125% of rated capacity and the overspeed governor and ' +
          'safety gear are tripped and verified before dispatch. The tests are then repeated on ' +
          'site after installation.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'trapped',
        question: 'What if someone is trapped?',
        answer:
          'Press the alarm. It connects to a battery-backed two-way intercom that reaches our ' +
          "service desk directly, independent of the building's power, 24 hours a day.",
        link_label: 'Request service',
        link_url: '/contact',
        scope: 'general',
      },
    ],
  },
  {
    id: 'maintenance',
    slug: 'maintenance',
    name: 'Maintenance & service',
    description: 'After the doors open.',
    questions: [
      {
        id: 'what-amc-covers',
        question: 'What does an AMC cover?',
        answer:
          'Scheduled preventive visits, adjustment, lubrication, rope and brake inspection, safety ' +
          'testing, and priority breakdown response. Comprehensive contracts include parts; ' +
          'non-comprehensive ones bill parts separately.',
        link_label: 'Talk about an AMC',
        link_url: '/contact',
        scope: 'general',
      },
      {
        id: 'service-frequency',
        question: 'How often should a lift be serviced?',
        answer:
          'Monthly for commercial and healthcare installations, quarterly at minimum for a home ' +
          'lift. Frequency is set by usage, not by the calendar alone.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'breakdown-response',
        question: 'How fast do you respond to a breakdown?',
        answer:
          'Our service desk is staffed 24/7 and we prioritise entrapments above everything else. ' +
          'Response times to site are set out in your maintenance contract.',
        link_label: 'Get service support',
        link_url: '/contact',
        scope: 'general',
      },
      {
        id: 'service-other-brands',
        question: 'Do you service lifts you did not install?',
        answer:
          'Yes, subject to a survey. We need to see the equipment and its history before we can ' +
          'take responsibility for it, and we will tell you honestly if something needs putting ' +
          'right before a contract starts.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'modernise-or-replace',
        question: 'Can an old lift be modernised instead of replaced?',
        answer:
          'Usually. Drive, controller, doors and interior can be replaced on the existing shaft, ' +
          'rails and structure — better ride and efficiency for a fraction of the disruption of a ' +
          'full replacement.',
        link_label: 'Discuss modernisation',
        link_url: '/contact',
        scope: 'general',
      },
      {
        id: 'spare-parts',
        question: 'Are spare parts available years later?',
        answer:
          'We hold parts for the systems we install and support them through their service life. ' +
          'This is one of the reasons we keep the range deliberately narrow.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
    ],
  },
  {
    id: 'pricing-enquiry',
    slug: 'pricing-enquiry',
    name: 'Pricing & enquiry',
    description: 'Cost, quotes and what happens next.',
    questions: [
      {
        id: 'how-much',
        question: 'How much does a lift cost?',
        answer:
          'Honestly, it depends on travel, capacity, drive type and finish, and the range is wide ' +
          'enough that any single number quoted here would mislead you. Send the floors and the ' +
          'building type and we will come back with a real figure rather than a bracket.',
        link_label: 'Get a quote',
        link_url: '/contact',
        scope: 'general',
      },
      {
        id: 'cost-drivers',
        question: 'What drives the cost most?',
        answer:
          'Number of stops first, then capacity, then finish. Going from a standard stainless car ' +
          'to a brass or stone interior changes the price meaningfully; adding a floor changes it ' +
          'more.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'installation-included',
        question: 'Is installation included in the quote?',
        answer:
          'Yes. Our quotes cover supply, installation and commissioning, and state clearly what is ' +
          'excluded — usually civil work, the power supply to the controller and any statutory ' +
          'fees.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'quote-validity',
        question: 'How long is a quote valid?',
        answer:
          'Typically 30 days, because steel and component pricing moves. The validity is stated on ' +
          'the quotation itself.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'after-enquiry',
        question: 'What happens after I submit an enquiry?',
        answer:
          'We review the drawings and the brief, call you to fill in what the form could not, ' +
          'recommend a system with reasons, and then quote against that recommendation.',
        link_label: '',
        link_url: '',
        scope: 'general',
      },
      {
        id: 'response-time',
        question: 'How quickly will someone get back to me?',
        answer:
          'Within one working day for project enquiries. Service and breakdown calls are answered ' +
          '24/7 on the service line.',
        link_label: '',
        link_url: '',
        scope: 'contact',
      },
      {
        id: 'upload-drawings',
        question: 'Can I upload drawings with my enquiry?',
        answer:
          'Yes — PDF, JPG, PNG, WEBP, DWG and DXF, up to six files of 10 MB each. Plans and ' +
          'sections are the two most useful things you can send.',
        link_label: '',
        link_url: '',
        scope: 'contact',
      },
      {
        id: 'existing-lift',
        question: 'I have an existing lift, not a new project.',
        answer:
          'Use the service route rather than the project enquiry form. It reaches our service desk ' +
          'directly instead of the sales pipeline.',
        link_label: '',
        link_url: '',
        scope: 'contact',
      },
      {
        id: 'factory-visit',
        question: 'Can I visit the factory?',
        answer:
          'Yes, by appointment. Seeing cars being fabricated and load-tested tells you more about ' +
          'a lift company than any brochure.',
        link_label: '',
        link_url: '',
        scope: 'contact',
      },
      {
        id: 'site-visit-before-quote',
        question: 'Do you do site visits before quoting?',
        answer:
          'For anything beyond a straightforward new-build shaft, yes. It is the only reliable way ' +
          'to quote a retrofit.',
        link_label: '',
        link_url: '',
        scope: 'contact',
      },
    ],
  },
]

/**
 * Categories with their questions, optionally narrowed to one scope.
 *
 * Without a scope every question is returned, contact-scoped ones included —
 * which is what /faq, /lifts and the product pages have always shown. Empty
 * categories are kept rather than dropped so a caller looking up a section by
 * slug still finds it; the pages that render chips already filter on count.
 */
export function faqCategories(scope) {
  return FAQ_CATEGORIES.map((category) => {
    const questions = scope
      ? category.questions.filter((q) => q.scope === scope)
      : category.questions
    return { ...category, questions, count: questions.length }
  })
}

/** One section by slug, e.g. 'choosing-a-lift'. Undefined if there is no such slug. */
export function faqCategory(slug) {
  return faqCategories().find((category) => category.slug === slug)
}

export default FAQ_CATEGORIES
