# wos-state-discord-bot
**Note this project is not affiliated with Whiteout Survival or Century Games**
> A bot to manage Whiteout Survival discord servers


## Features
### Restricted access - request to join
Restrict access to the discord server. Only the ones allowed will receive a `state <state number i.e 1234>` and a `<Alliance code i.e ABC> Member`. Setup permissions revolving these roles. There are two methods to give people access to the Discord server:
- request to join
  - Only the ones accepted will receive state and alliance roles
- invite code to join
  - Only the ones with a valid onetime invite codes will receive state and alliance roles

### Giftcodes in chat + redeem through Discord
Bot send valid giftcodes to the giftcodes text channel, with a button to redeem it instantly with the in-discord selected connected WOS account

### Terms and condition administration
Via the command `/admin_panel` you can create a terms and condition dashboard in the current channel. When you do, a new message will appear through which you can create new drafts and publish them into the terms and condition channel.

Note this should be used in a private text channel with only moderators and admins. Each draft is a Discord text channel thread. Everything you send in the thread will be 1:1 replicated into the terms and conditions text channel whenever you hit publish and select that specific draft version.

### In discord admin panel
With the command `/admin_panel` admins can configure the bot
- Mange alliance whitelist (allowed to request to join via "request to join" feature
- Set invite channel
  - Which is the channel the bot create invite codes for if the feature "invite code to join" is used
- Set giftcode channel
  - Set the text chanel where the bot should send found redeemable giftcodes
- Set T&C channel
  - Set the channel where terms and conditions should be sent by the bot
- Create T&C dashboard here
  - Used to create a dashboard to manage terms and condition drafts, and to publish
- Set join request category
  - Set the channel category under which it should create text channels used to allow alliances to allow/reject new recruits into the Discord server

## Setup
### Environment variables
The environment variables which has to be set up in order to run this application

| Environment variable | Description                                          | Required |
| -------------------- | ---------------------------------------------------- | -------- |
| WOSBOT_DISCORD_TOKEN | The Discord token generated from the Discord website | Yes      |

### Get started

#### 1. Install python
Install python from https://python.org (Python 3.12 used during development but feel free to try other versions!)

#### 2. Set up a virtual environment for Python (optional)
Either in the wos-state-discord-bot folder, parent folder, or somewhere else fitting, run the following in cmd.exe or another terminal.

This will create a virtual environment for the bot.

```
python -m venv wosbot
```

This will activate the environment

Windows Powershell:
```
.\wosbot\Scripts\activate.ps1
```

Cmd (Windows Command Prompt):
```
.\wosbot\Scripts\activate.bat
```

Linux:
```
./wosbot/Scripts/activate
```

#### 3. Install the required external packages for running the bot

Run this in the bot folder
```
python -m pip install -r requirements.txt
```

#### 5. Set the environment variables
Set the required environment variables. See the environment variables section further up


#### 6. Run the bot
Run this in the bot folder and the bot should go online!
```
python main.py
```
