/**
 * What is certified, and by whom — the Quality section on /about and the Trust
 * band on the home page.
 *
 * `reference` is deliberately not a certificate number. Publishing one invites
 * it to be quoted back after it has lapsed; "available on request" is both
 * truthful and current.
 */

const CERTIFICATIONS = [
  {
    id: 'iso-9001',
    name: 'ISO 9001 — Quality Management System',
    issuer: 'Independent certification body',
    reference: 'Certificate available on request',
    description:
      'Design, manufacture, installation and servicing of passenger and goods lifts operate ' +
      'under a documented quality management system, audited annually.',
  },
  {
    id: 'load-overspeed',
    name: 'Load and overspeed testing',
    issuer: 'In-house test bench',
    reference: '',
    description:
      'Every car is load-tested to 125% of rated capacity, and the overspeed governor and safety ' +
      'gear are tripped and verified before dispatch.',
  },
  {
    id: 'inspection-licensing',
    name: 'Lift inspection and licensing',
    issuer: 'Telangana State Electrical Inspectorate',
    reference: '',
    description:
      'Installations are prepared for, and handed over against, statutory inspection and ' +
      'licensing under the applicable state lift rules.',
  },
]

export default CERTIFICATIONS
