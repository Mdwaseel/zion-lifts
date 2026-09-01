/**
 * What Zion does after the doors open — the service band on /about and home.
 *
 * `icon` is a key into `PILLAR_ICONS` in `components/icons.jsx`, not a filename.
 * An icon that is not in that map falls back to the shield rather than
 * rendering nothing, so a typo here degrades quietly.
 */

const SERVICE_PILLARS = [
  {
    id: 'service-24-7',
    slug: 'service-24-7',
    name: '24/7 breakdown support',
    icon: 'wrench',
    description:
      'A staffed service desk every hour of the year, with entrapments prioritised above all ' +
      'other calls.',
    detail: 'Answered by a person, not a queue.',
  },
  {
    id: 'amc',
    slug: 'amc',
    name: 'Annual maintenance contracts',
    icon: 'calendar',
    description:
      'Scheduled preventive visits covering ropes, brakes, doors, levelling, the pit and the ' +
      'intercom, with safety testing recorded.',
    detail: 'Comprehensive and non-comprehensive options.',
  },
  {
    id: 'breakdown',
    slug: 'breakdown',
    name: 'Breakdown response',
    icon: 'bolt',
    description:
      'Priority attendance under contracted response times, with the parts we hold for the ' +
      'systems we install.',
    detail: 'Response times stated in the contract.',
  },
  {
    id: 'modernisation',
    slug: 'modernisation',
    name: 'Modernisation',
    icon: 'refresh',
    description:
      'New drive, controller, doors and interior on the existing shaft and rails — better ride ' +
      'and efficiency without a full replacement.',
    detail: 'Typically at 20–25 years.',
  },
  {
    id: 'spares',
    slug: 'spares',
    name: 'Spare parts',
    icon: 'box',
    description: 'Parts held and supported through the service life of every system we install.',
    detail: 'Deliberately narrow range, deeply supported.',
  },
]

export default SERVICE_PILLARS
