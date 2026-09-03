import { useEffect } from 'react'

import { ClientLogos, TestimonialRow } from '@/components/sections'
import { useApi } from '@/lib/hooks'

import { Hero, WorldBelow } from './home/Ascent'
import { Cabin } from './home/Cabin'
import { AfterInstall, FinalAscent, People, Trust } from './home/Human'
import { Configurator, Engineering, Machine } from './home/Machine'
import { Blueprint, Certifications, Details, ProjectsReel } from './home/Proof'
import './home/home.css'

export default function Home() {
  const { data: lifts } = useApi('lifts/')
  const { data: projects } = useApi('projects/')
  const { data: finishes } = useApi('finishes/')
  const { data: pillars } = useApi('service-pillars/')
  const { data: team } = useApi('team/')
  const { data: certifications } = useApi('certifications/')
  const { data: partners } = useApi('partners/')
  const { data: testimonials } = useApi('testimonials/')

  useEffect(() => {
    document.title = 'Zion Lifts — Engineered to rise'
  }, [])

  return (
    <>
      <Hero />
      <WorldBelow />
      <Machine lifts={lifts ?? []} />
      <Engineering />
      <Cabin />
      <Configurator finishes={finishes ?? []} />
      <Blueprint />
      <Certifications />
      <ProjectsReel projects={projects ?? []} />
      <Details />
      <AfterInstall pillars={pillars ?? []} />
      <People team={team ?? []} />
      <TestimonialRow testimonials={(testimonials ?? []).slice(0, 3)} />
      <ClientLogos />
      <Trust certifications={certifications ?? []} partners={partners ?? []} />
      <FinalAscent />
    </>
  )
}
