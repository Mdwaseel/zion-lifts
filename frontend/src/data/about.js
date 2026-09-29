/**
 * The company's own account of itself, as published on zionlifts.com/about —
 * rendered by /about. Wording is kept close to the original; only spelling
 * and punctuation are tidied.
 *
 * Media paths point into `frontend/public/media/`. The `motion/` films are
 * rendered from the Remotion project in `/motion` (npm run render).
 */

export const ESTABLISHED = 2011

export const WHO_WE_ARE = {
  opening: 'Zion Lifts® is one of the latest additions to the ever-growing elevator industry of India.',
  body: [
    'Zion was established in 2011 and is into the design, manufacture, supply, erection and installation of all types of lifts.',
    'The company is managed by senior management cadre and elevator technocrats who have worked in the elevator field for more than two and a half decades, supported by top-class, experienced engineers and professionals.',
    'The determined effort of our team and the quest for excellence have got us where we are today. With our technical know-how and vast knowledge, we are proficient in understanding unique needs and challenging demands.',
  ],
  founder: { name: 'Varghese', role: 'Founder & CEO' },
}

/** "World-class, current-generation elevator solutions for …" — the sectors, each with a building to
    show it and the lifts it usually takes ([slug, label]) */
export const SECTORS = [
  {
    name: 'Residential buildings',
    line: 'Homes, villas and apartment blocks — lifts sized to the family and finished to the interior.',
    src: '/media/frames/kashi-exterior.jpg',
    lifts: [['home-elevator', 'Home elevator'], ['capsule-elevator', 'Capsule elevator'], ['hydraulic-elevator', 'Hydraulic elevator'], ['car-lift', 'Car lift']],
  },
  {
    name: 'Commercial & corporate towers',
    line: 'Daily peaks, group control and lobbies that have to look the part.',
    src: '/media/contexts/context-office.jpg',
    lifts: [['passenger-elevator', 'Passenger elevator'], ['belt-lift', 'Belt lift'], ['mrl-traction', 'MRL traction']],
  },
  {
    name: 'Industries',
    line: 'Goods and freight lifts from 500 kg to 5,000 kg, built for daily abuse.',
    src: '/media/contexts/context-industrial.jpg',
    lifts: [['goods-elevator', 'Goods & freight'], ['hydraulic-elevator', 'Hydraulic elevator']],
  },
  {
    name: 'Malls',
    line: 'Scenic and capsule lifts that are part of the view, and service lifts behind the scenes.',
    src: '/media/sourced/place-mall.jpg',
    pos: 'center 40%',
    lifts: [['capsule-elevator', 'Capsule elevator'], ['passenger-elevator', 'Passenger elevator']],
  },
  {
    name: 'Hotels',
    line: 'Guest lifts, service lifts and dumbwaiters, running to different schedules.',
    src: '/media/contexts/context-hotel.jpg',
    lifts: [['passenger-elevator', 'Passenger elevator'], ['dumbwaiter', 'Dumbwaiter']],
  },
]

export const MODERNISATION = {
  body: [
    'Apart from new installations, Zion also undertakes the modernisation of old lifts and the servicing and maintenance of elevators. Our engineers are well experienced and have been serving this industry for the better part of two decades.',
    'We offer a wide range of world-class, current-generation elevator solutions for:',
  ],
  closing:
    'Over the past decade, safety and quality have been of foremost importance to us, and always will be. Because of our commitment to our vision and values, we have helped our clients with their elevator needs from scratch to the get-go — hassle-free, using only the finest technology and innovation.',
}

/** "Our core value system" */
export const VALUES = [
  {
    name: 'Team',
    body: 'We are backed by a team of efficient and diligent professionals, which plays an important part in delivering optimum quality to our customers.',
    src: '/media/frames/workshop-assembly.jpg',
  },
  {
    name: 'Safety',
    body: 'Our people work day in and out for the customers who use our elevators every day. Safety for our customers and employees is our topmost priority.',
    src: '/media/frames/chilkuru-lop.jpg',
  },
  {
    name: 'Integrity',
    body: 'Every employee, whatever their position or responsibility, embraces our code of conduct. We believe in a formal but open relationship with our employees and our customers alike.',
    src: '/media/frames/lekha-inuse.jpg',
  },
  {
    name: 'Quality',
    body: 'We adhere strictly to the quality of our materials and accept no compromise. We aim to reflect that quality in our products — it is what we are known for.',
    src: '/media/frames/kashi-machine.jpg',
  },
  {
    name: 'Attitude',
    body: 'Being a valuable partner to our customers takes hard-working, passionate people. We motivate and empower our people at every level to give their best and to make good decisions — growing them and the organisation together.',
    src: '/media/frames/workshop-frame.jpg',
  },
  {
    name: 'Professionalism',
    body: 'Our customers are what make us, and we do whatever it takes to keep them satisfied — products on time, honesty with our clients, quality, safety and standards.',
    src: '/media/frames/chath-entrance.jpg',
  },
]

/** "What we are known for" — in the order the grid lays them out: a photograph
    where the promise is about people or a finished lift, one of the /motion
    drawings where it is about a mechanism */
export const KNOWN_FOR = [
  { id: 'workforce', text: 'A technically sound workforce.', src: '/media/frames/workshop-frame.jpg', wide: true },
  { id: 'rescue', text: 'Automatic rescue devices and overload warning, wherever required.' },
  { id: 'standards', text: 'Superior standards, to the latest lift safety norms.' },
  { id: 'energy', text: 'The latest control systems, to energy-saving norms.' },
  { id: 'schedule', text: 'Strict adherence to the maintenance schedule and the contract.' },
  { id: 'custom', text: 'Custom lifts, built to the client’s demand.', src: '/media/frames/chilkuru-capsule.jpg', wide: true },
  { id: 'silent', text: 'Silent travel motion, in every lift.', src: '/media/frames/kashi-cabin.jpg', wide: true },
  { id: 'spares', text: 'Genuine spares for existing lifts, at a reasonable cost.', src: '/media/frames/kashi-machine.jpg', wide: true },
].map((k) =>
  k.src ? k : { ...k, film: `/media/motion/known-${k.id}-light.mp4`, poster: `/media/motion/known-${k.id}-light.jpg` },
)

/** Client reviews, as published on zionlifts.com — spelling tidied, words kept */
export const REVIEWS = [
  {
    name: "Saicharan Munnangi",
    quote:
      "First of all, I’m very grateful to be able to discover Zion Lifts. Right from the day of confirming the order to getting it installed in my house, it’s been very seamless. The technicians did a great job in installing the lift without any troubles for us. Appreciate your efforts for the amazing service and getting the job done on time.",
  },
  {
    name: "Bingi Venkatesh",
    quote:
      "Zion Elevators is an organisation run by individuals who are very passionate about delivering quality and safety in their products. Their knowledge and expertise of the whole elevator assembly and installation is great. Outstanding company and team.",
  },
  {
    name: "Naresh R",
    quote:
      "I think this is one of the best and most excellent elevator companies in Hyderabad. They take responsibility for lift and elevator repair works and service maintenance. Not only this, they offer to change old lifts to new lifts. Definitely they will do perfect work.",
  },
  {
    name: "Srinu N",
    quote:
      "We came to know about Zion when we started research on available options for elevators. We compared different brands on cost, features and service and found Zion to suit our requirements. Right from installation till date, they’ve a good process in place for installation and service. We’ve got exemplary service from the Zion team. Thank you.",
  },
  {
    name: "Cheruku Bhaskarreddy",
    quote:
      "These people are professionals in elevator maintenance — a very skilled and professional team. I’m proud to have them as my service provider. Thanks Zion, you guys are great.",
  },
  {
    name: "Lohitaksh K",
    quote:
      "They really stand up to their name and brand reputation. Their staff was so professional and easy to deal with. The lift in my home runs butter-smooth. Would recommend them to anyone who requires lifts of any kind.",
  },
  {
    name: "Vedant Tomar",
    quote:
      "We tried contacting many elevator companies who said it’s not possible to get a lift in our place because of low space. When my friend recommended Zion Lifts, we were a bit hesitant but called them for help — and we are glad we did. It’s been a year since they supplied the lift and it’s working butter-smooth. 100% recommended to anyone looking for a brand which provides trust and assurance.",
  },
  {
    name: "Radha Nandgirikar",
    quote:
      "I recommend Zion Lifts to anyone looking for a premium elevator experience with safety being the priority. They installed a hydraulic lift in my home last week and I’m very satisfied with the results. The staff were very experienced and punctual and made it according to our needs. It looks like a modern lift with the latest technological features.",
  },
  {
    name: "Nagaraj Ashammagari",
    quote:
      "The installation went very well. The person was knowledgeable and got it installed in a timely manner. He was very good about showing us how it worked, making sure we got to ride it up and down to see all the different features it had. Zion Elevator was everything we desired.",
  },
  {
    name: "Elena Thomas",
    quote:
      "I am extremely impressed with the quality of production. Unlike other companies they respond and troubleshoot quickly.",
  },
  {
    name: "Jakkula Raju",
    quote:
      "Had a lot of issues with my elevator installer, always trouble with it. I was referred to Zion Elevators — these guys are really professionals and have solved the issue. Very prompt on call-backs and they give the best service. Thanks Zion.",
  },
  {
    name: "Ireni Ramesh",
    quote:
      "Very happy with the service from Zion’s customer relationship management team and erection team — timely completion, elevator riding comfort, and the product is very, very good.",
  },
]

export const OFFICES = {
  works: 'Plot No 4, Amar Jyoti Colony, Anand Nagar, New Bowenpally, Secunderabad, Telangana 500011',
  phones: ['+91 75690 08004', '+91 72079 99963'],
  email: 'info@zionlifts.com',
}
