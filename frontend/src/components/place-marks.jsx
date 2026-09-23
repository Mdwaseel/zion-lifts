/** Where a lift belongs — one mark per kind of building.

   Same 24px grid, 1.5 stroke and round caps as `icons.jsx`. Every stroke
   carries `pathLength="1"`, so a page can draw the mark in with a single
   dash-offset transition without measuring anything. Kept out of `icons.jsx`
   because only the lift pages use them. */

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

const mark = (paths) =>
  function PlaceMark({ size = 28, ...rest }) {
    return (
      <svg {...base} width={size} height={size} {...rest}>
        {paths.map((d) => (
          <path key={d} d={d} pathLength="1" />
        ))}
      </svg>
    )
  }

/** a pitched roof over a door */
export const VillaMark = mark(['M3 11.5 12 4l9 7.5', 'M5.5 9.6V20h13V9.6', 'M10 20v-5.2h4V20'])

/** a slab block, three floors of windows */
export const ApartmentMark = mark([
  'M6.5 20V4h11v16',
  'M3.5 20h17',
  'M9.6 8h1.2M13.2 8h1.2',
  'M9.6 11.6h1.2M13.2 11.6h1.2',
  'M9.6 15.2h1.2M13.2 15.2h1.2',
])

/** the bell on the desk */
export const HotelMark = mark(['M3.5 19.5h17', 'M5.5 16.5a6.5 6.5 0 0 1 13 0Z', 'M12 10V7.2', 'M10.4 7.2h3.2'])

/** a tower and its podium */
export const OfficeMark = mark([
  'M4.5 20V7.5l6.5-3V20',
  'M11 20v-9.5h8.5V20',
  'M3 20h18',
  'M7.7 10.5v.01M7.7 13.5v.01M7.7 16.5v.01',
  'M14 13.6h2.6M14 16.6h2.6',
])

/** a saw-tooth roof and a stack */
export const FactoryMark = mark(['M3 20h18', 'M4.5 20v-8.5l4.6 3v-3l4.6 3v-3l4.8 3.2V20', 'M16.4 12.6V5h2.4v9.2'])

/** the sign at the ramp */
export const ParkingMark = mark(['M7 4h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3Z', 'M10 16.6V7.6h2.7a2.7 2.7 0 0 1 0 5.4H10'])

/** a ward block under its cross */
export const HospitalMark = mark(['M5 20V6.5h14V20', 'M3 20h18', 'M12 9.2v5M9.5 11.7h5', 'M10.2 20v-2.8h3.6V20'])

/** a pediment on four columns */
export const CivicMark = mark(['M3.5 9.6 12 4.4l8.5 5.2Z', 'M6.2 12.4v5M10.1 12.4v5M13.9 12.4v5M17.8 12.4v5', 'M4 20h16'])

/** a load on the platform */
export const WeightMark = mark(['M8.2 8.5h7.6l2.7 11H5.5l2.7-11Z', 'M12 8.5a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8Z', 'M9.6 15h4.8'])

/** the alarm the lift answers to */
export const FlameMark = mark(['M12 3.5c.6 3.2 4.8 5.2 4.8 10a4.8 4.8 0 0 1-9.6 0c0-2 .9-3.3 2-4.4.2 1.5.9 2.4 1.8 2.8-.4-3 .1-6.2 1-8.4Z'])

/** application slug → mark, and the room that stands for it */
/* --- the enquiry forms' options: same grid, same stroke ------------------- */

/** an awning over a shop front */
export const ShopMark = mark(['M4 9.5 5.6 4.5h12.8L20 9.5', 'M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0', 'M5.5 12v8h13v-8', 'M10 20v-4.5h4V20'])

/** a set square on a drawing: still on paper */
export const DraftMark = mark(['M4 20 4 6.5 17.5 20Z', 'M7.6 16.8v-3.4l3.4 3.4Z', 'M13 4.5l6.5 6.5', 'M15.2 6.7l-1.6 1.6M17.4 8.9l-1.6 1.6'])

/** a tower crane: under construction */
export const CraneMark = mark(['M7 20V4', 'M4 20h6', 'M7 6h13', 'M7 6 3.5 8.5', 'M7 4l6 2', 'M17 6v6.5', 'M15.4 12.5h3.2v2.6h-3.2Z'])

/** a key: the building is ready */
export const KeyMark = mark(['M8.2 15.8a3.8 3.8 0 1 0 0-7.6 3.8 3.8 0 0 0 0 7.6Z', 'M12 12h8.5', 'M17.4 12v3M20.5 12v2.2'])

/** a lift car between its arrows */
export const LiftMark = mark(['M6.5 7.5h11V20h-11Z', 'M12 7.5V20', 'M9.6 4.8 12 2.6l2.4 2.2'])

/** a glazed capsule car */
export const CapsuleMark = mark(['M7 20V9a5 5 0 0 1 10 0v11Z', 'M7 12.5h10', 'M12 12.5V20', 'M5 20h14'])

/** a ram under a platform: hydraulic */
export const PistonMark = mark(['M5 7.5h14', 'M7 7.5v3.2h10V7.5', 'M12 10.7V16', 'M9 16h6v4H9Z', 'M5 20h14'])

/** a tray on a hatch: the dumbwaiter */
export const TrayMark = mark(['M5 5h14v14H5Z', 'M5 13.5h14', 'M8.5 13.5c0-2.4 1.6-4 3.5-4s3.5 1.6 3.5 4', 'M12 9.5V8.3'])

/** not sure yet */
export const HelpMark = mark(['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M9.6 9.4a2.5 2.5 0 1 1 3.6 2.3c-.8.4-1.2 1-1.2 1.9', 'M12 16.6v.2'])

/** a clock: no hurry */
export const ClockMark = mark(['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 7.2V12l3.2 2'])

/** a warning triangle: the lift is down */
export const AlertMark = mark(['M12 3.8 21 19.5H3Z', 'M12 9.6v4.6', 'M12 16.9v.2'])

export const PLACES = {
  villa: { Icon: VillaMark, src: '/media/contexts/context-villa.jpg' },
  apartment: { Icon: ApartmentMark, src: '/media/contexts/context-apartment.jpg' },
  hotel: { Icon: HotelMark, src: '/media/contexts/context-hotel.jpg' },
  office: { Icon: OfficeMark, src: '/media/contexts/context-office.jpg' },
  industrial: { Icon: FactoryMark, src: '/media/contexts/context-industrial.jpg' },
  parking: { Icon: ParkingMark, src: '/media/products/car-stacker-01.jpg' },
  hospital: { Icon: HospitalMark, src: '/media/contexts/context-hospital.jpg' },
  institutional: { Icon: CivicMark, src: '/media/frames/owaisi-lobby.jpg' },
}
