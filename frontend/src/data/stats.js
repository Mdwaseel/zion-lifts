/**
 * The small numeric proof points above /about and /projects.
 *
 * `count_from` is what makes a number animate up rather than appear: set it to
 * "0" and `StatRow` counts to `value` when the row enters the viewport. Leave it
 * out for anything that is not really a quantity — a year and "24/7" counting up
 * from zero would be nonsense.
 */

const STATS = [
  {
    id: 'about-founded',
    group: 'about',
    value: '2012',
    label: 'Founded',
    caption: 'Hyderabad, with one workshop and one idea.',
  },
  {
    id: 'about-installations',
    group: 'about',
    value: '1,750+',
    label: 'Installations',
    caption: 'Across homes, hospitals, hotels and factories.',
    count_from: '0',
  },
  {
    id: 'about-people',
    group: 'about',
    value: '95–100',
    label: 'People',
    caption: 'Engineers, fabricators, installers, service crew.',
  },
  {
    id: 'about-support',
    group: 'about',
    value: '24/7',
    label: 'After-sales support',
    caption: 'Breakdown cover, every day of the year.',
  },
  {
    id: 'about-certified',
    group: 'about',
    value: 'ISO',
    label: 'Certified',
    caption: 'Quality management across design and manufacture.',
  },

  {
    id: 'projects-installations',
    group: 'projects',
    value: '1,750+',
    label: 'Installations',
    count_from: '0',
  },
  { id: 'projects-since', group: 'projects', value: '2012', label: 'Building since' },
  { id: 'projects-sectors', group: 'projects', value: '6', label: 'Building sectors' },

  { id: 'home-installed', group: 'home', value: '1,750+', label: 'Lifts installed', count_from: '0' },
  { id: 'home-years', group: 'home', value: '13', label: 'Years building' },
  { id: 'home-cover', group: 'home', value: '24/7', label: 'Service cover' },
]

/** The stats for one page, in order. Mirrors the old `?group=` query. */
export function statsFor(group) {
  return STATS.filter((stat) => stat.group === group)
}

export default STATS
