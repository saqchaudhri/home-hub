# Preparing a Home Hub Pi to post

You set the Pi up at your house and post it. Whoever receives it plugs in the power and an ethernet cable, and nothing else. When it gets online it tells your iPhone, and you finish the setup remotely over Tailscale, for example with Claude Code.

You need:

- A Raspberry Pi 4 or 5 with power supply, and an SD card or SSD (32 GB or more).
- [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your Mac.
- `starter/dist/Home_Hub_starter.tar` and your check-in address in `starter/checkin-address.txt`.
- Tailscale running on your Mac (already done).

## At your house

1. **Install Home Assistant.** In Raspberry Pi Imager choose your Pi, then **Other specific-purpose OS → Home assistants and home automation → Home Assistant**, and write it to the card. Put the card in the Pi, plug it into your router with an ethernet cable, power it on, and wait a few minutes.

2. **Restore the starter.** Open http://homeassistant.local:8123 (if another Home Assistant already uses that name, find the Pi's address in your router). Choose **Upload backup**, pick `Home_Hub_starter.tar`, choose **Restore**, and wait for the Welcome screen to come back.

3. **Create your own login.** Choose **Create my smart home** and make an account for yourself; you'll use it to sign in remotely. For the location, enter the new house's town if you know it (you can change it later).

4. **Add Tailscale.**
   1. Go to **Settings → Add-ons → Add-on store → Tailscale → Install**.
   2. Turn on **Start on boot** and **Watchdog**, then choose **Start**.
   3. Open the add-on's **Log** tab, open the sign-in link it shows, and approve it with your Tailscale account.
   4. In the [Tailscale admin console](https://login.tailscale.com/admin/machines), find the new machine and use **⋯** to:
      - **Edit machine name**, for example `home-hub-yusuf`
      - **Disable key expiry**, so it never drops off your network

5. **Set up check-in.** Go to **Settings → Devices & services → Add integration → Home Hub check-in** and fill in:
   - **Name of this house**, for example "Yusuf's house"
   - **Check-in address**: the address in `starter/checkin-address.txt`
   - **Remote address**: `http://home-hub-yusuf:8123`, using the machine name from step 4

   Your iPhone gets a "Home Hub online" notification within a few seconds. That shows it works.

6. **Check remote access.** On your Mac, with Tailscale on, open `http://home-hub-yusuf:8123` and sign in.

7. **Shut it down.** Go to **Settings → System → ⋮ (top right) → Shut down**. Wait for the lights to settle, unplug it and post it with its power supply.

## At the new house

Plug the Pi into their router with an ethernet cable, then plug in the power. That's all.

## When your iPhone says "Home Hub online"

Tap the notification, or open the remote address on your Mac, and sign in. Then ask Claude Code to finish the setup, for example:

> Finish setting up Yusuf's Home Hub at http://home-hub-yusuf:8123

The remaining jobs:

- Set the right location, time zone and units (**Settings → System → General**).
- Create a login for the family (**Settings → People → Add person**, with **Allow login** on).
- Add their devices, and **Islamic Prayer Times**.
- Add **Browser Mod** and register the wall tablet. Someone at the house opens Home Assistant on the tablet, then **Browser Mod** in the sidebar, turns on **Register** and reloads.
- Run the **Home Hub** wizard.

You also get a "Home Hub online" notification whenever the Pi restarts, for example after a power cut, so you know it's back.
