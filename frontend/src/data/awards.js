const TOI_TBA_2021 =
  'https://timesofindia.indiatimes.com/business/india-business/times-business-awards-hyderabad-when-the-best-in-real-estate-get-recognized/articleshow/86550029.cms'
const INDUSTRY_OUTLOOK =
  'https://www.theindustryoutlook.com/manufacturing/vendor/zion-lifts-lift-manufacturer-supplier-with-advanced-manufacturing-capabilities-cid-3337.html'
const ISO_CERTIFICATE = '/media/press/apts-iso-certificate.webp'

/* Awards & recognition — read off the trophies, plaques and certificates in the
   office. The marks are the organisers' own logos (media/awards), trimmed to
   their ink; the photographs themselves are not shown. Newest first within
   each body, so the list reads as a record rather than a boast. */

export const AWARDS = [
  {
    id: 'tba-2024',
    logo: '/media/awards/times-business-2024.webp',
    body: 'Times Business Awards',
    year: '2024',
    title: 'Excellence in Lifts Manufacturers & Suppliers',
    note: 'The 10th edition, Hyderabad — presented by The Times of India.',
  },
  {
    id: 'tba-2023',
    logo: '/media/awards/times-business-2023.webp',
    body: 'Times Business Awards',
    year: '2023',
    title: 'Best Lifts Manufacturers & Suppliers',
    note: 'Hyderabad — the third year in a row the category came to Zion.',
  },
  {
    id: 'tba-2022',
    logo: '/media/awards/times-business-2022.webp',
    body: 'Times Business Awards',
    year: '2022',
    title: 'Best Lifts Manufacturers & Suppliers',
    note: 'Hyderabad — awarded for a second consecutive year.',
  },
  {
    id: 'tba-2021',
    logo: '/media/awards/times-business-2021.webp',
    body: 'Times Business Awards',
    year: '2021',
    title: 'Best Lifts Manufacturers & Suppliers',
    note: 'Hyderabad — our first Times Business Award, from The Times Group.',
    href: TOI_TBA_2021,
    cta: 'Read in The Times of India',
  },
  {
    id: 'io-2024',
    logo: '/media/awards/industry-outlook-2024.webp',
    body: 'Industry Outlook',
    year: '2024',
    title: 'Top 10 Elevators & Moving Stairways Manufacturers',
    note: 'For an unwavering focus on excellence in quality and delivery.',
    href: INDUSTRY_OUTLOOK,
    cta: 'Read in Industry Outlook',
  },
  {
    id: 'io-2022',
    logo: '/media/awards/industry-outlook-2022.webp',
    body: 'Industry Outlook',
    year: '2022',
    title: 'Top 10 Elevators & Escalators Manufacturers',
    note: 'Named among the ten, for excellence in quality and delivery.',
    href: INDUSTRY_OUTLOOK,
    cta: 'Read in Industry Outlook',
  },
  {
    id: 'apts-iso',
    logo: '/media/awards/apts-iso.webp',
    body: 'APTS Quality Certifications',
    year: 'ISO 9001:2015',
    title: 'Certified quality management',
    note: 'Sales, supply, erection, commissioning and after-sales support of elevators.',
    href: ISO_CERTIFICATE,
    cta: 'View the certificate',
  },
]

/* The home page's short version: one line per awarding body. */
export const RECOGNITION = [
  {
    id: 'tba',
    logo: '/media/awards/times-business-2024.webp',
    title: 'Best Lifts Manufacturers & Suppliers',
    body: 'Times Business Awards, Hyderabad',
    years: ['2021', '2022', '2023', '2024'],
  },
  {
    id: 'io',
    logo: '/media/awards/industry-outlook-2024.webp',
    title: 'Top 10 Elevator Manufacturers',
    body: 'Industry Outlook',
    years: ['2022', '2024'],
  },
]

/* In the press, and on record. Each opens in a new tab: the article where
   the publication has one online, otherwise the page itself at full size. */
export const PRESS = [
  {
    id: 'industry-outlook-2021',
    thumb: '/media/press/industry-outlook-2021-720.webp',
    source: 'Industry Outlook · Elevator Manufacturers, May 2021',
    title: 'Zion Lifts — providing state-of-the-art elevators with unmatched quality',
    href: INDUSTRY_OUTLOOK,
    cta: 'Read on Industry Outlook',
  },
  {
    id: 'feature-scaling-new-heights',
    thumb: '/media/press/feature-scaling-new-heights-720.webp',
    source: 'Newspaper feature',
    title: 'Zion Lifts — scaling new heights by prioritising quality, safety and service',
    href: '/media/press/feature-scaling-new-heights.webp',
    cta: 'View the page',
  },
  {
    id: 'feature-quality-and-service',
    thumb: '/media/press/feature-quality-and-service-720.webp',
    source: 'Newspaper feature',
    title: 'Zion Lifts, where quality and service can be trusted with guarantee on safety',
    href: '/media/press/feature-quality-and-service.webp',
    cta: 'View the page',
  },
  {
    id: 'apts-iso-certificate',
    thumb: '/media/press/apts-iso-certificate-720.webp',
    source: 'APTS Quality Certifications',
    title: 'ISO 9001:2015 — Certificate of Registration',
    href: ISO_CERTIFICATE,
    cta: 'View the certificate',
  },
]
