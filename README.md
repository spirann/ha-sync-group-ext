# Sync Switch & Light Group

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/spirann/ha-sync-group-ext/actions/workflows/validate.yml/badge.svg)](https://github.com/spirann/ha-sync-group-ext/actions/workflows/validate.yml)

A small Home Assistant custom integration inspired by
[avishorp/sync_group](https://github.com/avishorp/sync_group), built around
a **Main + members** model and extended to work across both `switch.*` and
`light.*` entities.

## What's new in v4

- You can now optionally **link an existing switch/light entity as an
  additional master**, alongside the auto-created Main entity. This
  matters when the "all on/all off" trigger can come from somewhere Main
  never sees directly - a physical wall switch reporting its own state, a
  scene, or another integration/automation acting straight on that
  entity. The linked master is treated exactly like Main: triggering it
  turns every member to match, and it's kept mirroring Main (and vice
  versa) at all times.
- Same unavailability rules now apply to the linked master too: a flip to
  `unavailable`/`unknown` (or back) is never treated as a trigger.

## What's new in v3

- Each group now creates a real **"Main" switch entity** instead of asking
  you to pick an existing entity to act as master. That means Main gets all
  the normal helper trappings: it can be renamed, moved to an **area**,
  given **labels**/a **category**, or **disabled**, all through its own
  entity settings dialog - no separate config needed for any of that.
- "Master" / "slave" wording has been renamed to **Main** / **members**
  throughout.
- Each group's Main entity has a stable, unique ID (`entry_id`), and the
  config entry itself is given a unique ID at creation time, so it behaves
  like a proper registered helper rather than an anonymous one.
- You can set an icon for Main right when you create the group (and change
  it later, either from the group's options or straight from the entity's
  own settings).

> **Upgrading from v1/v2/v3:** the config format changed again in v3 (no
> more picking an existing "master" entity - a new Main entity is created
> instead) and gained an optional field in v4 (linked master). Existing v3
> groups keep working after upgrading to v4 (the linked master field just
> defaults to "none"); v1/v2 groups still need to be removed and recreated.

## What it does

Each group has:

- a **Main** entity, created automatically by this integration;
- an optional **linked master** - an existing switch/light entity of yours
  that acts as a second, equally-valid trigger point, for cases where the
  "on"/"off" can originate outside of Main (a physical device, a scene, an
  automation acting on that entity directly, etc.);
- one or more **member** entities (any mix of switches and lights you
  already have) that follow along.

- **Main or the linked master triggered** (turned on or off - by you, an
  automation, voice assistant, a physical button, whatever): every member
  is set to match, and the other of the pair (Main <-> linked master) is
  kept mirroring the same value.
- **Member triggered**: the other members are left completely alone. Main
  (and the linked master, if configured) are updated to reflect reality:
  - If that leaves *every* member off, Main/linked master turn off.
  - If a member turns on (for example, everything was off and you flip one
    member on), Main/linked master turn on too - but the other members
    stay off.

Only on/off state is ever touched - light attributes such as brightness,
color temperature or color are left alone, so a dumb switch and a
color-capable light can happily share a group.

## Unavailability handling

- An entity going `unavailable`/`unknown` is ignored completely - it never
  triggers anything, and is simply skipped when broadcasting (or when
  computing what Main/the linked master's value should be). This applies
  equally to Main, the linked master, and every member.
- An entity *coming back* from `unavailable`/`unknown` and reporting its
  restored state is **not** treated as a trigger either - only an observed
  on -> off or off -> on flip, from an entity that was already known to be
  on or off, counts as a real trigger.

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS -> Integrations -> ⋮ -> Custom
   repositories**.
2. Add `https://github.com/spirann/ha-sync-group-ext` as the repository
   URL, category **Integration**.
3. Find **"Sync Switch & Light Group"** in HACS and click **Download**.
4. Restart Home Assistant.

### Manually

1. Copy the `custom_components/sync_group_ext` folder from this repo into
   your Home Assistant `config/custom_components/` directory (so you end
   up with `config/custom_components/sync_group_ext/manifest.json`).
2. Restart Home Assistant.

### Setting up a group

1. Go to **Settings -> Devices & Services -> Add Integration** (or
   **Helpers -> Add Helper**), search for **"Sync Switch & Light Group"**.
2. Give the group a name, optionally pick an icon, optionally pick a
   **linked master** entity, then pick one or more **member** entities.
3. A new `switch.<name>` entity appears - that's Main. Set its area,
   labels, category, or icon from its own entity settings, exactly like
   any other helper.
4. Repeat for as many groups as you need - each one is its own config
   entry and creates its own Main entity.

To change the icon, linked master, or member list later, open the
integration entry and click **Configure**. To rename Main, move it to an
area, or set its category, use the entity's own settings (gear icon)
instead - that's now a first-class entity, so it works the same way as any
other helper.

## About the missing icon in the "Add Helper"/"Add Integration" picker

The icon shown next to an integration's *name* in the "Add Integration" /
"Add Helper" search list (before you've even configured anything) is not
something a custom integration's code controls - Home Assistant's core
frontend fetches those from the community-maintained
[`home-assistant/brands`](https://github.com/home-assistant/brands)
repository. Now that this project is a public GitHub repo, submitting an
`icon.png`/`logo.png` there via PR is possible if you want that polish -
just ask and I'll prepare the assets.

What *is* already there is the entity-level icon: once a group is created,
its Main switch shows the icon you picked (or the default `mdi:sync`) in
the entity list, dashboards, etc., and you can change it any time.

## Notes / limitations

- Sync is on/off only; it doesn't try to merge or average brightness/color
  between different lights.
- If you toggle two members at almost the same instant, Main's reflected
  state follows whichever change Home Assistant processes last - no
  different from two people flipping two switches at once.
- Main's state is restored across Home Assistant restarts (via the normal
  restore-state mechanism), and re-checked against its members as soon as
  they're available again.

## Contributing

Issues and PRs welcome at
[github.com/spirann/ha-sync-group-ext](https://github.com/spirann/ha-sync-group-ext).

## License

[MIT](LICENSE)
