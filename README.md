# Home Hub

A setup wizard for Home Assistant that builds a family's **wall-tablet** and **phone** dashboards from their own devices: dark glass design, clock, prayer times, weather, family calendar, lights, heating, cameras, music, and a photo screensaver with an **ON AIR** sign when the office door is shut.

It also runs, by itself:

- **Doorbell popup**: the camera full screen on the wall tablet when the doorbell rings, even over the screensaver
- **Azan**: played on the main speaker at prayer times, with a Mute button on phone notifications and a Stop azan button on the dashboards
- **Night mode**: the tablet's screensaver becomes a dim clock overnight
- **Outdoor lights**: on at sunset, off at sunrise, and put right after a power cut

## Before you start

Install these from **HACS → Frontend** (the wizard warns you if any are missing):

- button-card
- Mushroom
- card-mod
- WallPanel

Optional:

- **Islamic Prayer Times** (Settings → Devices & services → Add integration) for the prayer card and the azan.
- **browser_mod** (HACS → Integrations) for the doorbell popup. After installing it, open Home Assistant on the wall tablet once so it appears in the wizard.
- The **Home Assistant app** on each phone that should get azan notifications.

## Install

**At a brand-new house:** use the starter backup. It sets everything up from Home Assistant's Welcome screen; see [starter/INSTALL.md](starter/INSTALL.md).

**Posting a ready-made Pi:** prepare it at your house with Tailscale and **Home Hub check-in**, and post it. The family plugs in power and ethernet, your phone is told it's online, and you finish the setup remotely; see [starter/PREPARE_PI.md](starter/PREPARE_PI.md).

**With HACS:**
1. HACS → ⋮ → **Custom repositories** → paste `https://github.com/saqchaudhri/home-hub`, type **Integration**.
2. Search for **Home Hub**, download it, then restart Home Assistant.

**By hand:**
1. Copy the `custom_components/home_hub` folder into your Home Assistant `config/custom_components/` folder (for example with the Samba share or File editor add-on).
2. Restart Home Assistant.

## Set up

Settings → Devices & services → **Add integration** → **Home Hub**. The first time, Home Hub looks through the house's devices and fills in its best guesses on every page (people, lights by room, heating, the likeliest cameras, a speaker that can play the azan, the bin calendar, outdoor lights and so on), so mostly it's a matter of checking each page. The wizard asks, page by page:

1. House name and your first name (for the ON AIR sign)
2. The people who live there
3. Lights and smart sockets
4. Heating
5. Cameras and battery levels
6. Weather, family calendar, bin calendar, prayer times
7. Main speaker, white noise, other speakers and TVs
8. Doorbell: the doorbell sensor, the wall tablet, and how long to show the camera
9. Azan: which prayers (Fajr is left out to start with), the recording, and the phones to notify
10. Night mode times and outdoor lights
11. Which dashboards to create, screensaver photos, and the office door sensor

It then adds **Wall tablet** and **Phone** to the sidebar, and a **Home Hub** device with:

- **Azan playing** (on while it plays)
- **Stop azan** (a button)
- **Wall tablet mode** (day or night; change it by hand any time, and it goes back on schedule at the next switchover)

To change anything later: Settings → Devices & services → **Home Hub** → **Configure**. Running the wizard again rebuilds both dashboards, replacing any changes made to them by hand. Restarting Home Assistant never does.

Screensaver photos come from **Media → My media**.

## Notes

- Home Hub never touches dashboards it didn't create. If one already exists at `/home-hub-wall` or `/home-hub-phone`, it is left alone and that dashboard is skipped.
- Removing Home Hub deletes the two dashboards it made and stops everything it runs.
- Stop azan only stops the speaker if it's the azan playing, so it never cuts off music.
- If the speaker can't play the azan, the phones are still notified.
- Home Hub manages the two dashboards' names and sidebar entries, so don't change them in Settings → Dashboards. To remove one, run the wizard again and untick it.

## Home Hub check-in

A separate small integration (`extras/custom_components/home_hub_checkin`, kept apart because HACS allows one integration per repository; it travels in the starter backup). When Home Assistant starts, it sends one "online" message to a webhook on the installer's own Home Assistant, retrying until it gets through, so the installer gets a phone notification as soon as a posted Pi is plugged in. The installer's side is a webhook automation that sends the notification.

## Coming next

Publishing on GitHub for HACS.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install pytest-homeassistant-custom-component esprima
.venv/bin/python -m pytest
```

`reference/` holds exports of the original dashboards and is never published.

### Building the starter backup

1. Put HACS's `hacs.zip` unpacked in `starter/downloads/hacs/unzipped`, and browser_mod's source zip unpacked in `starter/downloads/browser_mod/unzipped`.
2. Run `python3 starter/build_starter.py`. It writes `starter/dist/Home_Hub_starter.tar`.

It holds Home Hub, HACS, browser_mod, the four cards (registered as dashboard resources) and a minimal `configuration.yaml`. There are no accounts, so Home Assistant asks for a new login after restoring. `starter/restore-test/` is a blank Home Assistant for checking that a restore works.
