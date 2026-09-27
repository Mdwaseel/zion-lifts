import { AbsoluteFill, Composition, registerRoot } from 'remotion'

import { HERO, Hero } from './Hero'
import { KNOWN, TILE } from './KnownFor'
import { MODERNISE, Modernise } from './Modernise'

/* the drawn films again, on the site's ivory: inverting the frame and turning
   the hue half a circle keeps the teal teal and turns the ground to paper */
const LIGHT = ['known-standards', 'known-energy', 'known-rescue', 'known-schedule']
const onPaper = (Comp) =>
  function OnPaper() {
    return (
      <AbsoluteFill style={{ filter: 'invert(1) hue-rotate(180deg) saturate(1.25)' }}>
        <Comp />
      </AbsoluteFill>
    )
  }

function Root() {
  return (
    <>
      <Composition id="about-hero" component={Hero} durationInFrames={HERO.frames} fps={HERO.fps} width={HERO.width} height={HERO.height} />
      <Composition
        id="about-modernise"
        component={Modernise}
        durationInFrames={MODERNISE.frames}
        fps={MODERNISE.fps}
        width={MODERNISE.width}
        height={MODERNISE.height}
      />
      {KNOWN.map((k) => (
        <Composition key={k.id} id={k.id} component={k.component} durationInFrames={k.frames} fps={TILE.fps} width={TILE.width} height={TILE.height} />
      ))}
      <Composition
        id="about-modernise-light"
        component={onPaper(Modernise)}
        durationInFrames={MODERNISE.frames}
        fps={MODERNISE.fps}
        width={MODERNISE.width}
        height={MODERNISE.height}
      />
      {KNOWN.filter((k) => LIGHT.includes(k.id)).map((k) => (
        <Composition
          key={`${k.id}-light`}
          id={`${k.id}-light`}
          component={onPaper(k.component)}
          durationInFrames={k.frames}
          fps={TILE.fps}
          width={TILE.width}
          height={TILE.height}
        />
      ))}
    </>
  )
}

registerRoot(Root)
