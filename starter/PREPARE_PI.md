# Preparing a Home Hub Pi to post

You set the Pi up at your house and post it. Whoever receives it plugs in the power and an ethernet cable, and nothing else. When it gets online it tells your iPhone, and you finish the setup remotely over Tailscale, for example with Claude Code.

You need:

- A Raspberry Pi 4 or 5 with power supply, and an SD card or SSD (32 GB or more).
- [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your Mac.
- `starter/dist/Home_Hub_starter.tar` and your check-in address in `starter/checkin-address.txt`.
- Tailscale running on your Mac (already done).

Preparing several Pis? Make a golden image once (see [the golden image](#preparing-several-pis-the-golden-image) at the end), and each Pi then takes about 5 minutes.

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

## Preparing several Pis: the golden image

Set up one Pi, copy its card to an image file, and write that image to every new card. Each Pi then only needs its own Tailscale sign-in and check-in name, about 5 minutes at your house.

Each Pi has to sign in to Tailscale on its own. A copied card that's already signed in gives every Pi the same identity, and they knock each other off your network. Home Assistant's Tailscale add-on has no built-in sign-in key option, so the image has the add-on installed but not signed in.

### Make the image (once per Pi model)

The Pi 4 and Pi 5 run different versions of Home Assistant, so make one image for each model you use. Use a small card, 32 GB, for the golden Pi: the image is as big as the card, and every card you write it to must be at least that size.

1. **Set up the golden Pi.** Do steps 1–3 above: install Home Assistant, restore the starter, and create your login.
2. **Install Tailscale but don't sign in.** Go to **Settings → Add-ons → Add-on store → Tailscale → Install**. Turn on **Start on boot** and **Watchdog**. Don't choose Start, and don't use its sign-in link.
3. **Skip check-in for now.** It's already installed by the starter; each Pi gets its own name later.
4. **Shut it down.** Go to **Settings → System → ⋮ → Shut down**, wait for the lights to settle, then take the card out.
5. **Copy the card to your Mac.** Put the card in your Mac (choose **Ignore** if macOS says it can't read it), then in Terminal:

   Find the card. It's the **external, physical** disk of about 32 GB, for example `/dev/disk4`:

   ```bash
   diskutil list external physical
   ```

   Unmount it (put your disk number in place of 4):

   ```bash
   diskutil unmountDisk /dev/disk4
   ```

   Copy and compress it. This only reads from the card. It asks for your Mac password and takes 10–20 minutes:

   ```bash
   sudo dd if=/dev/rdisk4 bs=4m status=progress | gzip -1 > ~/Home_Hub_golden_pi5.img.gz
   ```

   Eject it:

   ```bash
   diskutil eject /dev/disk4
   ```

   Keep `Home_Hub_golden_pi5.img.gz` somewhere safe. It contains your Home Assistant login, so treat it like a password and don't share or upload it.

### Each Pi you post

1. **Write the image.** In Raspberry Pi Imager choose your Pi, then **Choose OS → Use custom** and pick the `.img.gz` file, then the new card, then **Next**. If it offers OS customisation settings, choose **No**.
2. **Boot it at your house** with an ethernet cable, and wait a few minutes.
3. **Sign in to Tailscale.** Open http://homeassistant.local:8123 and sign in with your login. Go to **Settings → Add-ons → Tailscale** (it starts by itself; if it isn't running, choose **Start**), open the **Log** tab and approve the sign-in link. In the [Tailscale admin console](https://login.tailscale.com/admin/machines), give the machine its own name (for example `home-hub-yusuf`) and **Disable key expiry**.
4. **Set up check-in** as in step 5 above, with this house's name and remote address. Your iPhone confirms it works.
5. **Shut it down and post it.**

After posting, it's the same as before: plug in, your iPhone says "Home Hub online", and you finish the setup remotely.

Good to know:

- **Your login:** every Pi from the image starts with the same login (yours). When you finish setting one up, you can change its password under your profile.
- **Updating the image:** when Home Hub gets a new version, either update it on each Pi remotely, or remake the image from an updated golden Pi.
