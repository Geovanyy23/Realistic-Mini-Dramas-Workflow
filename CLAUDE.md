# CLAUDE.md

Read `skills/realistic-mini-dramas/SKILL.md` first. Rules that do not bend:
- `./mini-drama validate` and `./mini-drama plan --dry-run` are the only commands that run unattended. They spend nothing.
- Never construct or arm `VideoExpressAdapter` outside an owner-approved live run. Never in dry mode.
- Preserve `project.model_label.requested` verbatim ("Fable 5.1 for Claude" in the pilot). `observed` stays `null` until read from the live form.
- Unknown = `null`. Do not invent seeds, settings, costs, job ids or results.
- Nothing from `private/` or `.state/` is committed. Run `./mini-drama privacy-scan` before packaging.
- Tests: `python3 -m unittest discover -s tests -v` (no third-party deps required; `jsonschema` used if present).
- Pushing, PRs, community publication and real generation each require a separate explicit owner authorization.
