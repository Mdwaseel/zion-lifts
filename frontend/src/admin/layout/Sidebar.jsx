import { NavLink, useLocation } from 'react-router-dom'

/**
 * Navigation, built from the server's registry.
 *
 * The groups and their order come from `resources.py`, so registering a model
 * puts it in the sidebar — there is no list of links to keep in step.
 *
 * A collection that declares a `section` is deliberately absent: it is a tab on
 * another collection's screen, not a destination. The server has already
 * filtered those out of this payload — see `AdminRegistry.grouped`.
 *
 * `unread` badges the two collections that fill up on their own. Everything
 * else changes because somebody here changed it, so a count on it would be
 * their own work reported back to them.
 */

export default function Sidebar({ groups, open, onNavigate, unread = {} }) {
  // A section's tabs live behind one sidebar entry, so the entry has to stay
  // lit while you are on any of them — otherwise opening Finishes appears to
  // navigate away from the sidebar entirely, with nothing highlighted.
  const { pathname } = useLocation()
  const current = pathname.replace(/^\/control\/?/, '').split('/')[0]

  return (
    <nav
      id="cf-sidebar"
      className={`cf-sidebar${open ? ' is-open' : ''}`}
      aria-label="Sections"
    >
      <NavLink
        to="/control"
        end
        className={({ isActive }) => `cf-nav__link cf-nav__link--home${isActive ? ' is-active' : ''}`}
        onClick={onNavigate}
      >
        Overview
      </NavLink>

      {/* Written here rather than derived from the registry, like Overview
          above it: analytics is a screen that asks questions of the visit
          tables, not a collection anyone edits, so there is no resource for the
          server to have listed. */}
      <NavLink
        to="/control/analytics"
        className={({ isActive }) => `cf-nav__link cf-nav__link--home${isActive ? ' is-active' : ''}`}
        onClick={onNavigate}
      >
        Analytics
      </NavLink>

      {groups.map((group) => (
        <div key={group.group} className="cf-nav__group">
          <h2 className="cf-nav__heading">{group.group}</h2>
          <ul>
            {group.resources.map((resource) => {
              const owns = (resource.tabs ?? []).some((tab) => tab.key === current)
              const count = unread[resource.key] ?? 0
              return (
                <li key={resource.key}>
                  <NavLink
                    to={`/control/${resource.key}`}
                    className={({ isActive }) =>
                      `cf-nav__link${isActive || owns ? ' is-active' : ''}`
                    }
                    onClick={onNavigate}
                  >
                    <span className="cf-nav__label">{resource.label_plural}</span>
                    {count > 0 && (
                      <span
                        className="cf-nav__badge"
                        // The number alone reads as "12" beside "Enquiries",
                        // which a screen reader announces as a quantity of
                        // nothing in particular.
                        aria-label={`${count} unread`}
                      >
                        {count > 99 ? '99+' : count}
                      </span>
                    )}
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </div>
      ))}

      <div className="cf-nav__group">
        <h2 className="cf-nav__heading">Elsewhere</h2>
        <ul>
          <li>
            {/* Django's admin is still there and still works; anything the
                panel does not cover is reachable from here. */}
            
          </li>
          <li>
            <a className="cf-nav__link" href="/" target="_blank" rel="noreferrer">
              View site ↗
            </a>
          </li>
        </ul>
      </div>
    </nav>
  )
}
