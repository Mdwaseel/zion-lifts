# Static site content

Six collections that used to be Django models, an admin screen and a public API
endpoint each. Nothing about them changed between deploys — a certification is
issued once, the company was founded once, and a privacy policy is amended by a
lawyer, not by an operator at 4pm. Paying for a table, a migration, a serializer,
an endpoint, a network round trip and an admin form to render text that never
moves was the wrong trade, so they live here instead.

Each module exports plain data in exactly the shape the page already consumed,
so the components that read them are unchanged apart from the import.

| Module            | Renders on                          |
| ----------------- | ----------------------------------- |
| `faqs.js`         | /faq, /contact, /lifts, /lifts/:slug |
| `stats.js`        | /about, /projects                   |
| `milestones.js`   | /about                              |
| `certifications.js` | /about, /                         |
| `servicePillars.js` | /about, /                         |
| `legal.js`        | /privacy, /terms, /cookies          |

**Editing:** change the data here and redeploy. There is no admin screen for
these, by design. Anything that genuinely needs to change without a deploy —
lifts, projects, blogs, testimonials, offices, site settings — is still in the
control room.
