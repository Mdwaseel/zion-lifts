/**
 * The company timeline, rendered by the Journey section on /about.
 *
 * Chronological, and each entry carries the still that shows on the stage while
 * it is selected. `image_url` points into `frontend/public/media/` — a renamed
 * file leaves a hole on the page, so keep the two in step.
 */

const MILESTONES = [
  {
    id: 'founded',
    year: '2012',
    title: 'Zion Lifts is founded',
    description:
      'Started in Hyderabad with a small workshop, a handful of engineers and a straightforward ' +
      'purpose: to help people move better, safer and more comfortably.',
    image_url: '/media/frames/kashi-floor.jpg',
  },
  {
    id: 'manufacturing',
    year: '2014',
    title: 'First manufacturing unit',
    description:
      "Fabrication is brought in-house so car frames, cabins and structural shafts are built to " +
      "Zion's own tolerances rather than bought in.",
    image_url: '/media/frames/owaisi-doors.jpg',
  },
  {
    id: 'commercial',
    year: '2016',
    title: 'Commercial and institutional work',
    description:
      'The range widens beyond homes into offices, hotels and healthcare, which brings group ' +
      'control, stretcher cars and heavier duty cycles with it.',
    image_url: '/media/frames/owaisi-lobby.jpg',
  },
  {
    id: 'service-desk',
    year: '2018',
    title: '24/7 service desk',
    description:
      'A dedicated after-sales operation is established, with an out-of-hours line and an ' +
      'entrapment-first response policy.',
    image_url: '/media/frames/chilkuru-panel.jpg',
  },
  {
    id: 'mrl-standard',
    year: '2020',
    title: 'Gearless MRL becomes the standard',
    description:
      'Machine-room-less gearless traction is adopted as the default across the passenger range, ' +
      'for quieter, more efficient and lower-maintenance installations.',
    image_url: '/media/frames/kashi-drive.jpg',
  },
  {
    id: 'capsule',
    year: '2022',
    title: 'Glass and capsule programme',
    description:
      'Structural glazed shafts and panoramic cars become a distinct line of work as architects ' +
      'start treating the lift as part of the room.',
    image_url: '/media/frames/chilkuru-atrium.jpg',
  },
  {
    id: 'installations-1750',
    year: '2024',
    title: '1,750+ installations',
    description:
      'Zion passes 1,750 installations across residential, commercial, hospitality, healthcare and ' +
      'industrial buildings, with a team of 95–100 people.',
    image_url: '/media/frames/lekha-cabin.jpg',
  },
]

export default MILESTONES
