# Little Log for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/nils-frank/ha-little-log/actions/workflows/validate.yml/badge.svg)](https://github.com/nils-frank/ha-little-log/actions/workflows/validate.yml)
[![Test](https://github.com/nils-frank/ha-little-log/actions/workflows/test.yml/badge.svg)](https://github.com/nils-frank/ha-little-log/actions/workflows/test.yml)

Home Assistant integration for [Little Log](https://little-log.de/), bringing your
baby's sleep state into Home Assistant and letting you log events from anywhere in your
home.

## What is Little Log?

[Little Log](https://little-log.de/) is a baby tracking app: *"Schlaf erfassen, das
nächste Schlaffenster abschätzen, den Verlauf sehen"* - record sleep, estimate the next
sleep window, see the history.

You log what happens during the day (sleep, crying, bottles, nursing, diapers, tired
cues like yawning) and the app turns that into a picture of the day: how long the baby
has been awake, when the next nap is likely due, and how today compares to the usual
rhythm. The forecast is the part that makes it more than a logbook, since the awake
window between naps is what most sleep routines hang on.

Little Log offers a token-based integration API, which is what this project talks to.

> Little Log is an app by Lukas Reindl. This Home Assistant integration is an
> unofficial community project by Nils Frank and is not built, endorsed or
> supported by the app's author. Bugs in the integration belong in [this repo's
> issue tracker](https://github.com/nils-frank/ha-little-log/issues), not with the
> app.

## Why use it from Home Assistant?

Reaching for your phone to log a nap is exactly the moment you do not want to be holding
a phone. With this integration you can:

- Put a physical button on the nursery wall and wire it to `little_log.sleep_toggle`,
  so one press starts or ends the nap.
- Log a bottle or diaper change from a wall tablet dashboard.
- Have the current state on your Lock Screen as an iOS Live Activity (see below).
- Ask a voice assistant, or have an automation announce the app's own summary sentence
  over a speaker.
- Use the sleep state in unrelated automations: dim the hall lights while the baby
  sleeps, pause the vacuum, mute the doorbell.

## Features

- Config flow with a live token check, so a bad token is rejected before the entry is
  created, and reauthentication when a token is revoked later.
- `sensor.baby_state` polled every 60 seconds (the interval the vendor recommends),
  carrying the full status payload as attributes.
- Ten buttons for the argument-free commands, usable the moment the integration is set
  up, with no automation or dashboard wiring.
- Ten actions mapping 1:1 onto the API, all of them able to backdate an event.
- Every action can return the API's `speech_de` sentence through `response_variable`,
  ready to hand to a TTS or notification action.

## Requirements

- Home Assistant 2025.2 or newer.
- A Little Log account and an integration token.

## Installation

### HACS

This integration is not in the default HACS list yet, so it is added as a custom
repository. The button below opens the dialog in your own Home Assistant with the
repository prefilled:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nils-frank&repository=ha-little-log&category=integration)

Click it, confirm **Add**, then **Download**, and restart Home Assistant.

<details>
<summary>Manual HACS steps, if the button does not work</summary>

The button relies on [My Home Assistant](https://my.home-assistant.io/), which needs to
be enabled in your instance. Otherwise:

1. Open **HACS**.
2. Three-dot menu at the top right > **Custom repositories**.
3. Repository: `https://github.com/nils-frank/ha-little-log`, type: **Integration**.
4. **Add**, then search HACS for **Little Log** and **Download** it.
5. Restart Home Assistant.

</details>

### Manual

Copy `custom_components/little_log` into your Home Assistant `config/custom_components/`
directory and restart.

### Adding the integration

After installing and restarting, either click:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=little_log)

or go to **Settings > Devices & services > Add integration** and search for
**Little Log**.

## Getting a token

Generate an integration token in Little Log's **Settings** tab. The token looks like
`bt_...` and is issued per device, so you can revoke the one you gave Home Assistant
without touching your other devices or the account itself.

Paste it into the config flow. The integration validates it with a live `GET /status`
call, and tells you whether the token was rejected or the API was unreachable, rather
than failing later with a broken entity.

Keep the token out of version control and off shared dashboards. It grants write access
to your log.

## Entities

One sensor and ten buttons, all on a single **Little Log** device.

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.baby_state` | `awake` or `asleep` | `since_utc`, `elapsed_min`, `last_sleep`, `today`, `say` |

The buttons cover every command that needs no arguments, so they work straight from the
device page or a dashboard with nothing to wire up:

| Button | Sends |
| --- | --- |
| `button.little_log_toggle_sleep` | `POST /sleep/toggle` |
| `button.little_log_start_sleep` | `POST /sleep/start` |
| `button.little_log_stop_sleep` | `POST /sleep/stop` |
| `button.little_log_start_crying` | `POST /cry/start` |
| `button.little_log_stop_crying` | `POST /cry/stop` |
| `button.little_log_bottle` | `POST /bottle` |
| `button.little_log_nursing` | `POST /nursing` with `side: next` |
| `button.little_log_diaper` | `POST /diaper`, which the API logs as medium/medium |
| `button.little_log_yawn` | `POST /cue` with `subtype: yawn` |
| `button.little_log_undo` | `POST /undo` |

Pressing a button refreshes the sensor immediately rather than waiting out the poll
interval.

Use the actions below instead when you need to backdate an event, pick a diaper kind or
a nursing side, or read the API's `speech_de` reply, since a button entity cannot take
parameters or return a value.

`say` is a dictionary of ready-to-read German sentences generated by the app
(`summary`, `state`, `last_sleep`, `forecast`, `today`, `diaper`, `bottle`, `nursing`).
They are passed through untouched, which makes them a convenient TTS source but means
their language follows the app, not your Home Assistant locale.

The sensor is unavailable while the API cannot be reached; a revoked token starts a
reauthentication flow instead of failing silently.

## Actions

All actions take the optional timing fields below, except `undo`:

| Field | Type | Notes |
| --- | --- | --- |
| `minutes_ago` | 0-720 | Backdate the event. Defaults to now. |
| `at_utc` | timestamp | Exact time, as an alternative to `minutes_ago`. A value without a time zone is read in Home Assistant's own time zone and converted to UTC. |
| `config_entry_id` | config entry | Only needed when more than one Little Log token is configured. |

| Action | Extra fields | Effect |
| --- | --- | --- |
| `little_log.sleep_start` | - | Starts a sleep period. |
| `little_log.sleep_stop` | - | Ends the current sleep period. |
| `little_log.sleep_toggle` | - | Starts or ends sleep depending on the current state. Ideal for one physical button. |
| `little_log.cry_start` | - | Starts a crying period. |
| `little_log.cry_stop` | - | Ends a crying period. |
| `little_log.bottle` | - | Logs a bottle feeding. |
| `little_log.cue` | `subtype` (required, e.g. `yawn`) | Logs a tired cue. |
| `little_log.diaper` | `kind` (`wet`/`dirty`/`both`/`dry`) **or** `pee_level` + `poop_level` (`none`/`light`/`medium`/`full`, or `0`-`3`) | Logs a diaper change. With no fields the API defaults to medium for both levels. |
| `little_log.nursing` | `side` (`next`/`left`/`right`, default `next`) | Logs a nursing session. `next` alternates from the last recorded side. The API's own `L`/`R` spellings are accepted too. |
| `little_log.undo` | - | Reverses the last command sent with this token, within 10 minutes of it. |

`kind` and the `pee_level`/`poop_level` pair are two ways of describing the same change,
so they cannot be combined; the two level fields must be given together.

Every action supports an optional response containing the API's payload, including
`speech_de`:

```yaml
actions:
  - action: little_log.sleep_toggle
    data:
      minutes_ago: 5
    response_variable: result
  - action: tts.speak
    target:
      entity_id: tts.google_translate_de
    data:
      media_player_entity_id: media_player.nursery
      message: "{{ result.speech_de }}"
```

A button that toggles sleep:

```yaml
automation:
  - alias: "Nursery button toggles sleep"
    triggers:
      - trigger: state
        entity_id: binary_sensor.nursery_button
        to: "on"
    actions:
      - action: little_log.sleep_toggle
```

## Example dashboard

[`examples/dashboard.yaml`](examples/dashboard.yaml) is a complete dashboard covering
every command, plus the current state, the app's own summary and forecast sentences, and
a today overview. It uses the button entities where a command takes no arguments, and
calls the action directly where one does.

To use it: **Settings > Dashboards > Add dashboard**, open it, **Edit**, then the
three-dot menu > **Raw configuration editor**, and paste the file over what is there.

It uses built-in cards only, so it needs nothing from HACS beyond this integration, and
it references only `sensor.baby_state` and the `little_log.*` actions, so there is
nothing to rename unless you gave the sensor a different entity id.

This is also the dashboard the Live Activity recipe below points at with `data.url`,
since the Live Activity card cannot carry buttons of its own.

## iOS Live Activity

This integration ships no iOS code. Live Activities come entirely from the official
[Home Assistant Companion app's Live Activity support](https://companion.home-assistant.io/docs/notifications/live-activities/):
you write an automation that calls `notify.mobile_app_<your_device>` whenever
`sensor.baby_state` changes, and the Companion app renders the result on the Lock Screen
and in the Dynamic Island.

The essentials:

- Use a stable `data.tag`. Updates with the same tag replace the same activity instead of
  stacking new ones.
- `data.live_update: true` is what targets the Live Activity surface instead of a normal
  alert banner.
- `data.chronometer: true` together with `data.when: <timestamp>` renders a native ticking
  `mm:ss`/`hh:mm:ss` timer on the card.
- Trigger on state changes, plus a periodic refresh (every 5 minutes is plenty) and
  `homeassistant.start`, so the card survives restarts and stays current.
- End the activity by sending `message: "clear_notification"` with the same `tag`.

Cosmetic fields: `data.notification_icon` (an MDI slug), `data.notification_icon_color`,
`data.background_color`, `data.text_color`, and `data.url` for the tap destination.

```yaml
automation:
  - alias: "Baby Live Activity"
    triggers:
      - trigger: state
        entity_id: sensor.baby_state
      - trigger: time_pattern
        minutes: "/5"
      - trigger: homeassistant
        event: start
    actions:
      - action: notify.mobile_app_your_device
        data:
          message: "{{ state_attr('sensor.baby_state', 'say').summary }}"
          data:
            tag: little-log-live
            live_update: true
            chronometer: true
            when: >-
              {{ (as_timestamp(state_attr('sensor.baby_state', 'since_utc'))) | int }}
            notification_icon: >-
              {{ 'mdi:sleep' if is_state('sensor.baby_state', 'asleep') else 'mdi:sleep-off' }}
            background_color: "#1c1c1e"
            text_color: "#ffffff"
            url: /lovelace/baby
```

Replace `notify.mobile_app_your_device` with your own device's notify service and
`/lovelace/baby` with the dashboard you want the card to open.

### Styling and the ticking timer

`chronometer` has no style options. You cannot force a dark card, hide the seconds or
change the timer format. If you want an always-dark card, or a non-ticking "since N min"
text instead of a live timer, leave `chronometer` out and put a pre-formatted string in
`data.message`, for example:

```yaml
message: >-
  {{ state_attr('sensor.baby_state', 'say').forecast }}
  ({{ state_attr('sensor.baby_state', 'elapsed_min') }} min)
```

That text only changes when the automation fires, so keep the periodic trigger to refresh
it.

### Known limitation: no buttons on the Live Activity card

`data.actions`, the actionable-notifications mechanism behind buttons on a normal alert
(a doorbell notification, say), does **not** attach interactive buttons or long-press
actions to a Live Activity's persistent card. That mechanism applies only to regular
alert banners, which are a different UI from the fixed native ActivityKit widget layout.
This was confirmed on a live device, not only read in the docs. There is no supported way
to add a long-press "start/stop sleep" action to the Live Activity card itself.

The workaround is `data.url`: point it at a dashboard holding Start/Stop and quick-trigger
buttons wired to this integration's actions, so one tap on the card lands on the
controls. [`examples/dashboard.yaml`](examples/dashboard.yaml) is a ready-made one; a
minimal version is just:

```yaml
type: grid
columns: 2
square: false
cards:
  - type: button
    name: Toggle sleep
    icon: mdi:power-sleep
    tap_action:
      action: perform-action
      perform_action: little_log.sleep_toggle
  - type: button
    name: Bottle
    icon: mdi:baby-bottle-outline
    tap_action:
      action: perform-action
      perform_action: little_log.bottle
  - type: button
    name: Diaper (wet)
    icon: mdi:human-baby-changing-table
    tap_action:
      action: perform-action
      perform_action: little_log.diaper
      data:
        kind: wet
  - type: button
    name: Undo
    icon: mdi:undo
    tap_action:
      action: perform-action
      perform_action: little_log.undo
```

## Icon

The integration ships Little Log's own app icon in
`custom_components/little_log/brand/`, rendered from the app's `favicon.svg` at 256x256
and 512x512.

Home Assistant 2026.3 and newer pick these up automatically; local brand images take
priority over the CDN and need no manifest key. On older versions, and in HACS's own
store listing, the icon is served from
[brands.home-assistant.io](https://brands.home-assistant.io/), which requires a pull
request adding `custom_integrations/little_log/` to the
[home-assistant/brands](https://github.com/home-assistant/brands) repository. Until then
older instances show a generic placeholder, which is cosmetic only.

## Notes on the API

The integration talks to `https://little-log.de/api/integration/v1`.

Little Log was previously published as "Baby Tracker" on
`https://lukas-reindl.de/babytracker/`. That old API URL now answers with a cross-host
301 redirect, and HTTP clients strip the `Authorization` header on a cross-host redirect,
which turns a perfectly valid token into a misleading 401. The client therefore calls the
new host directly and refuses to follow a redirect away from it rather than silently
retrying without credentials.

Only `GET /status` and the `speech_de` field of command responses have a documented
shape. Everything else is modelled with optional fields and passed through unchanged, and
non-2xx responses other than 401/403 are reported generically. Places where behaviour is
assumed rather than confirmed are marked with a comment in the code.

## Development

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-test.txt ruff
.venv/bin/pytest
.venv/bin/ruff check .
```

CI runs `pytest`, `ruff`, `hassfest` and the HACS validation action on every push and
pull request.

## License

[MIT](LICENSE)
