import { createContext, useContext, useEffect, useState } from 'react'

import { get } from './api'

const SiteContext = createContext(null)

/** Sensible values so the shell renders before /api/site/ resolves. */
const FALLBACK = {
  company_name: 'Zion Lifts',
  tagline: 'Engineered to rise.',
  statement: 'Helping people move the right way — safer, quieter, better.',
  phone: '+91 75690 08004',
  whatsapp: '917569008004',
  email: 'info@zionlifts.com',
  email_service: 'service@zionlifts.com',
  founded_year: 2012,
  installations: 1750,
  team_size: '95–100',
  city: 'Hyderabad',
  country: 'India',
  offices: [],
}

export function SiteProvider({ children }) {
  const [site, setSite] = useState(FALLBACK)

  useEffect(() => {
    let live = true
    get('site/')
      .then((data) => live && data && setSite({ ...FALLBACK, ...data }))
      .catch(() => {
        /* keep the fallback — the shell must never be blank */
      })
    return () => {
      live = false
    }
  }, [])

  return <SiteContext.Provider value={site}>{children}</SiteContext.Provider>
}

export function useSite() {
  return useContext(SiteContext) ?? FALLBACK
}
