# quill-bot
A bot designed for quoting but ended up doing a bit more.

## Usage
Add the bot to your server with [this link](https://discord.com/api/oauth2/authorize?client_id=1096665287597768704&permissions=0&scope=bot%20applications.commands).

## Commands
- `/quote from quote [channel]`: Adds a quote to the \[channel\], serverwide quotes channel, or current channel, whichever one exists.
- `Quote message`: From a message context menu (e.g. right click or three dots), choose "Apps" and "Quote message" to have this message quoted in the serverwide quotes channel (if exists) or current channel.
- `/settings`: Manages settings for the server. *(WIP)*
- `/xkcd [id] [random]`: Retrieves an [XKCD](https://xkcd.com) webcomic. Defaults to retrieving the latest one; you can specify an \[id\] (number in URL) or let the bot retrieve a \[random\] one.
