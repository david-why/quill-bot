from interactions import (
    ComponentContext,
    Embed,
    EmbedField,
    Extension,
    InteractionContext,
    StringSelectMenu,
    StringSelectOption,
    component_callback,
    slash_command,
)

from client import CustomClient
from database import User

TIMEZONES = []
for i in range(-11, 12):
    for j in range(1):
        TIMEZONES.append(
            StringSelectOption(
                label=f'UTC {i:+}:{j*30:02}',
                value=str(i * 60 + (-1 if i < 0 else 1) * j * 30),
            )
        )


class UserSettingsCommandExtension(Extension):
    bot: CustomClient

    def get_embed_and_components(self, user: User):
        timezone = user.timezone
        if timezone is None:
            tzinfo = 'No timezone set'
        else:
            hours = timezone // 60
            minutes = abs(timezone) % 60
            tzinfo = f'UTC {hours:+}:{minutes:02}'
        embed = Embed(
            title='User settings',
            description='Here are your user settings',
            fields=[EmbedField('Timezone', f'Your current timezone is: **{tzinfo}**')],
        )
        menu = StringSelectMenu(
            *TIMEZONES, placeholder='Timezone', custom_id='usersettings_timezone'
        )
        components = [menu]
        return embed, components

    @slash_command('usersettings', description='Edit settings for the user')
    async def usersettings_command(self, ctx: InteractionContext):
        user_id = ctx.user.id
        user = self.bot.database.get_user(user_id)
        embed, components = self.get_embed_and_components(user)
        await ctx.send(embeds=embed, components=components, ephemeral=True)

    @component_callback('usersettings_timezone')
    async def usersettings_timezone_callback(self, ctx: ComponentContext):
        tz = int(ctx.values[0])
        user_id = ctx.user.id
        user = self.bot.database.get_user(user_id)
        user.timezone = tz
        self.bot.database.set_user(user_id, user)
        embed, components = self.get_embed_and_components(user)
        await ctx.edit_origin(embeds=embed, components=components)


def setup(bot: CustomClient):
    UserSettingsCommandExtension(bot)
