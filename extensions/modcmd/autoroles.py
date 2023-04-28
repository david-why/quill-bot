from typing import List, cast

from interactions import (
    ActionRow,
    BaseComponent,
    ComponentContext,
    Button,
    ButtonStyle,
    Permissions,
    Embed,
    Extension,
    InteractionContext,
    Role,
    RoleSelectMenu,
    Guild,
    listen,
    slash_command,
    component_callback,
)
from interactions.api.events import MemberAdd, Component

from client import CustomClient

MAX_AUTOROLES = 24


class AutorolesExtension(Extension):
    bot: CustomClient

    async def get_embed_and_components(self, guild: Guild):
        settings = self.bot.database.get_guild_settings(guild.id)
        autoroles = settings.autoroles
        roles: List[Role] = []
        delete_roles: List[int] = []
        for role_id in autoroles:
            role = await guild.fetch_role(role_id)
            if role is not None:
                roles.append(role)
            else:
                delete_roles.append(role_id)
        if delete_roles:
            for role_id in delete_roles:
                autoroles.remove(role_id)
            self.bot.database.set_guild_settings(guild.id, settings)
        embed = Embed(
            title='Autoroles setup',
            description=f'There are currently {len(roles)} roles added when a new '
            'member joins.\nClick on a button to delete the role, or select a new '
            'role to add.',
        )
        components: List[BaseComponent] = []
        for role in roles:
            components.append(
                Button(
                    style=ButtonStyle.SECONDARY,
                    label=f'@{role.name}',
                    custom_id=f'ar_@{role.id}',
                )
            )
        select = RoleSelectMenu(custom_id='autoroles_add')
        components.append(select)
        rows = ActionRow.split_components(*components)
        return embed, rows

    @slash_command('autoroles', description='View and manage autoroles settings')
    async def autoroles_command(self, ctx: InteractionContext):
        guild = ctx.guild
        if guild is None:
            return ctx.send('You can only use it in a server!', ephemeral=True)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.send(embeds=embed, components=components)

    @component_callback('autoroles_add')
    async def autoroles_add_callback(self, ctx: ComponentContext):
        add_role = cast(Role, ctx.values[0])
        guild = ctx.guild
        assert guild is not None
        member = ctx.member
        if member is None:
            return await ctx.send('Wait, who was that?')
        if not member.has_permission(Permissions.MANAGE_GUILD):
            return await ctx.send(
                'You must have the Manage Server permission!', ephemeral=True
            )
        settings = self.bot.database.get_guild_settings(guild.id)
        if add_role.id in settings.autoroles:
            return await ctx.send('That role is already in autoroles!', ephemeral=True)
        if len(settings.autoroles) >= MAX_AUTOROLES:
            return await ctx.send(
                'Maximum number of autoroles reached!', ephemeral=True
            )
        settings.autoroles.append(add_role.id)
        self.bot.database.set_guild_settings(guild.id, settings)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @listen()
    async def on_autorole_component(self, event: Component):
        ctx = event.ctx
        if not ctx.custom_id.startswith('ar_@'):
            return
        del_role_id = int(ctx.custom_id[4:])
        guild = ctx.guild
        assert guild
        member = ctx.member
        if member is None:
            return await ctx.send('Wait, who was that?')
        if not member.has_permission(Permissions.MANAGE_GUILD):
            return await ctx.send(
                'You must have the Manage Server permission!', ephemeral=True
            )
        settings = self.bot.database.get_guild_settings(guild.id)
        if del_role_id not in settings.autoroles:
            return await ctx.send(
                'This role, somehow, is not in autoroles!', ephemeral=True
            )
        settings.autoroles.remove(del_role_id)
        self.bot.database.set_guild_settings(guild.id, settings)
        embed, components = await self.get_embed_and_components(guild)
        await ctx.edit_origin(embeds=embed, components=components)

    @listen()
    async def on_member_add(self, event: MemberAdd):
        member = event.member
        guild = event.guild
        settings = self.bot.database.get_guild_settings(guild.id)
        print('memberadd', member, guild, settings.autoroles)
        await member.add_roles(settings.autoroles, 'Quill autoroles')


def setup(bot: CustomClient):
    AutorolesExtension(bot)
