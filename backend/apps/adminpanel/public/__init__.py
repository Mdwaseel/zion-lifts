"""The public, read-only face of the same models the control room edits.

Kept in this app rather than a separate one so there is exactly one place that
owns the site's data: the models, the admin API over them, and the anonymous
API the React front end reads. The two APIs differ in what they allow, not in
what they know.
"""
