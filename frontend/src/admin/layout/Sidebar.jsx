import { NavLink } from 'react-router-dom'

/**
 * Navigation, built from the server's registry.
 *
 * The groups and their order come from `resources.py`, so registering a model
 * puts it in the sidebar — there is no list of links to keep in step.
 */

export default function Sidebar({ groups, open, onNavigate }) {
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

      {groups.map((group) => (
        <div key={group.group} className="cf-nav__group">
          <h2 className="cf-nav__heading">{group.group}</h2>
          <ul>
            {group.resources.map((resource) => (
              <li key={resource.key}>
                <NavLink
                  to={`/control/${resource.key}`}
                  className={({ isActive }) => `cf-nav__link${isActive ? ' is-active' : ''}`}
                  onClick={onNavigate}
                >
                  {resource.label_plural}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <div className="cf-nav__group">
        <h2 className="cf-nav__heading">Elsewhere</h2>
        <ul>
          <li>
            {/* Django's admin is still there and still works; anything the
                panel does not cover is reachable from here. */}
            <a className="cf-nav__link" href="/admin/" target="_blank" rel="noreferrer">
              Django admin ↗
            </a>
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
