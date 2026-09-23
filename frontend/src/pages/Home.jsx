import { useEffect } from 'react'

import { ClientLogos } from '@/components/sections'
import { useApi } from '@/lib/hooks'

import { Hero, WorldBelow } from './home/Ascent'
import { Cabin } from './home/Cabin'
import { AfterInstall, FinalAscent, People, Voices } from './home/Human'
import { Installations } from './home/Installations'
import { LiftsExperience } from './home/LiftsExperience'
import { Engineering } from './home/Machine'
import CabinStudio from './lift/CabinStudio'
import { Blueprint, Certifications, Details, ProjectsReel } from './home/Proof'
import './home/home.css'

export default function Home() {
  const { data: lifts } = useApi('lifts/')
  const { data: projects } = useApi('projects/')
  const { data: finishes } = useApi('finishes/')
  const { data: pillars } = useApi('service-pillars/')
  const { data: team } = useApi('team/')
  const { data: testimonials } = useApi('testimonials/')

  useEffect(() => {
    document.title = 'Zion Lifts — Engineered to rise'
  }, [])

  return (
    <>
      <Hero />
      <WorldBelow />
      <LiftsExperience lifts={lifts ?? []} />
      <Engineering />
      <Cabin />
      <CabinStudio finishes={finishes ?? []} />
      <Blueprint />
      <Certifications />
      <ProjectsReel projects={projects ?? []} />
      <Installations />
      <Details />
      <AfterInstall pillars={pillars ?? []} />
      <People team={team ?? []} />
      <Voices testimonials={testimonials ?? []} />
      <ClientLogos />
      <FinalAscent />
    </>
  )
}
