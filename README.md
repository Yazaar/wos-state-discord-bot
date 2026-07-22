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
