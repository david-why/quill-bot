# quill-bot
A bot designed for quoting but ended up doing a bit more.

## Adding to your server
Add the bot to your server with [this link](https://discord.com/api/oauth2/authorize?client_id=1096665287597768704&permissions=276220348416&scope=applications.commands%20bot).

## Commands
- `/quote from quote [channel]`: Adds a quote to the \[channel\], serverwide quotes channel, or current channel, whichever one exists.
- `Quote message`: From a message context menu (e.g. right click or three dots), choose "Apps" and "Quote message" to have this message quoted in the serverwide quotes channel (if exists) or current channel.
- `/settings`: Manages settings for the server. This includes setting the serverwide quotes channel.
- `/xkcd [id] [random]`: Retrieves an [XKCD](https://xkcd.com) webcomic. Defaults to retrieving the latest one; you can specify an \[id\] (number in URL) or let the bot retrieve a \[random\] one.
- `/time time`: Sends an embed that shows the time given in each user's local timezone. The sender needs to set their timezone with `/usersettings`; the viewers do not.
- `/usersettings`: Manages settings for the user. This includes setting the user's timezone.
- `/userpoll text [min] [max]`: Creates a poll that lets users vote for users. Optionally specify the \[min\] and \[max\] number of users allowed to vote for each time.
- `/info`: Shows the user info. This includes the `/chat` tokens and `/imagegen` generations used today (see below)
- `/react message emoji`: Lets Quill react to the message. Interestingly, this can be used to react with external emojis, as long as Quill is in that server as well.
- `/customreact message image name`: Reacts to the message with the given image and the given emoji name. This will create a temporary emoji, react with the emoji, and delete the emoji.

The following commands are used to create btnroles messages, an alternative to reaction roles that uses buttons. They require the bot to have the Manage Roles permission to use.
- `/btnroles setup`: Interactively setup a btnroles message.
- `/btnroles add message role label`: Adds a new role to the message with the button label.
- `/btnroles edit [title] [content]`: Edits the embed in the message, optionally changing the \[title\] and/or \[content\].
- `/btnroles editrole message index [role] [label] [delete]`: Edits the index-th (1-based) button in the message, optionally changing the \[role\] and/or \[label\] or \[delete\] it.

The following commands require the `GRAPH_CLIENT_ID` environment variable set to the Client ID of an Azure application registration. Optionally, `GRAPH_TENANT` can be set to restrict the features to a specific tenant.
- `/teams`: Connects a channel in the server to a Teams group chat. *WIP: Sometimes the subscription for Teams message dies?*

The following commands require the `OPENAI_TOKEN` environment variable set to an OpenAI API token.
- `/chat`: Starts a chat with `gpt-3.5-turbo`. WARNING: This eats tokens (and therefore your money) really fast! Reply to bot messages to continue chatting. Each user has a 10,000 token limit per day.
- `/imagegen prompt`: Generates an image with the DALL-E API with the prompt. The resolution is 512x512, so it costs you (at the time of writing) $0.018 per image. Each user has a 5 image limit per day.
