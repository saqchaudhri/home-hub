# Setting up Home Hub at a new house

You need:

- **Home Assistant** on a Raspberry Pi, a Home Assistant Green or Yellow, or any other supported device. It must be freshly installed and showing its Welcome screen.
- The file **Home_Hub_starter.tar**, on a USB stick, in a download, or anywhere the computer you set up from can reach.
- About half an hour.

## 1. Install Home Assistant

Follow the official guide for your device at https://www.home-assistant.io/installation/. Stop when you see the **Welcome!** screen at http://homeassistant.local:8123.

## 2. Restore the starter

1. On the Welcome screen choose **Upload backup**.
2. Pick **Home_Hub_starter.tar** and choose **Restore**.
3. Wait a few minutes while Home Assistant restarts. The Welcome screen comes back when it's done.

This adds Home Hub, the dashboard cards, browser_mod (for the doorbell popup) and HACS (for updates). It brings no accounts or devices from anyone else's house.

## 3. Create your login

On the Welcome screen choose **Create my smart home** and follow it through:

- Your name, a username and a password. This is your own login; nobody else has it.
- **Your home's location.** Prayer times, sunset and the weather all use it.

## 4. Add your devices

In **Settings → Devices & services**, add the things you want on the dashboards. Home Assistant finds many of them by itself and offers them at the top of the page.

- Lights and smart plugs, the heating, the cameras and doorbell, and the speakers and TV.
- **Islamic Prayer Times** (choose **Add integration** and search for it), for the prayer card and the azan.
- **Rooms:** giving each device a room (area) helps the wizard tell you where your lights are.

## 5. Tablet and phones

- **Wall tablet**, so the doorbell can pop up on it:
  1. Switch on browser_mod: **Settings → Devices & services → Add integration → Browser Mod**. It's added straight away.
  2. On the tablet, open Home Assistant in the web browser and sign in.
  3. Still on the tablet, open **Browser Mod** in the sidebar and turn on **Register**, then reload the page.
  4. The tablet now appears in the Home Hub wizard. Its name is a long code such as `browser_mod_1900b4ac_b8e8037c`, which is fine. If you later clear the tablet's browser data or open Home Assistant at a different address, do step 3 again and re-run the wizard.
- **Phones:** install the **Home Assistant** app and sign in, so each phone can get the azan notification.

## 6. Run the Home Hub wizard

**Settings → Devices & services → Add integration → Home Hub.**

Home Hub looks through your devices and fills in its best guesses on every page. Go through each page, fix anything that's wrong, and choose **Next**. When you finish, **Wall tablet** and **Phone** appear in the sidebar.

To change anything later: **Settings → Devices & services → Home Hub → Configure**.

## 7. Finishing touches

- **Screensaver photos:** add photos under **Media → My media**.
- **On the wall tablet:** open **Wall tablet** from the sidebar and keep it on that page.
- **Updates (optional):** **Settings → Devices & services → Add integration → HACS**, then sign in with a free GitHub account when it asks. HACS then tells you when Home Hub and the cards have updates.
