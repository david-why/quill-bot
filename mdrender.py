import html
import json
import urllib.parse
from typing import Dict, List, Tuple, cast

from discord_markdown_ast_parser import parse
from discord_markdown_ast_parser.parser import Node, NodeType
from interactions import Guild
from bs4 import Tag, BeautifulSoup


def _wrap(text: str) -> Tuple[str, str]:
    return f'<{text}>', f'</{text}>'


CONTAINERS: Dict[NodeType, Tuple[str, str]] = {
    NodeType.ITALIC: _wrap('i'),
    NodeType.BOLD: _wrap('b'),
    NodeType.UNDERLINE: _wrap('u'),
    NodeType.STRIKETHROUGH: _wrap('s'),
    NodeType.SPOILER: ('<span style="background:black;color:black;">', '</span>'),
    NodeType.CODE_INLINE: _wrap('code'),
    NodeType.QUOTE_BLOCK: _wrap('blockquote'),
    NodeType.CODE_BLOCK: _wrap('pre'),  # TODO add attachment
}

MENTIONS: Dict[NodeType, Tuple[str, str]] = {
    NodeType.USER: _wrap('discord-user'),
    NodeType.ROLE: _wrap('discord-role'),
    NodeType.CHANNEL: _wrap('discord-channel'),
}

with open('emojis.json') as f:
    EMOJIS: Dict[str, str] = json.load(f)


def _render(node: Node) -> str:
    match node.node_type:
        case NodeType.TEXT:
            text = cast(str, node.text_content)
            return html.escape(text).replace('\n', '<br/>')
        case key if key in CONTAINERS:
            children = cast(List[Node], node.children)
            inner = ''.join(_render(child) for child in children)
            before, after = CONTAINERS[key]
            return f'{before}{inner}{after}'
        case key if key in MENTIONS:
            before, after = MENTIONS[key]
            return f'{before}{node.discord_id}{after}'
        case NodeType.URL_WITH_PREVIEW | NodeType.URL_WITHOUT_PREVIEW:
            url = cast(str, node.url)
            quoted = urllib.parse.quote(url, safe=':/')
            escaped = html.escape(url)
            return f'<a href="{quoted}">{escaped}</a>'
        case NodeType.EMOJI_CUSTOM:
            emoji_id = cast(int, node.discord_id)
            url = f'https://cdn.discordapp.com/emojis/{emoji_id}.png'
            return f'<img src="{url}" width="20" height="20"/>'
        case NodeType.EMOJI_UNICODE_ENCODED:
            emoji_name = cast(str, node.emoji_name)
            if emoji_name not in EMOJIS:
                return f':{emoji_name}:'
            return EMOJIS[emoji_name]
        case _:
            raise ValueError(f'Unknown node: {node!r}')


def convert_to_html(text: str) -> str:
    ast = parse(text)
    return ''.join(_render(node) for node in ast)


async def convert_with_guild(text: str, guild: Guild) -> str:
    text = convert_to_html(text)
    soup = BeautifulSoup(text, 'html.parser')
    for item in soup.select('discord-user'):
        user_id = item.text
        user = await guild.fetch_member(user_id)
        item.clear()
        if user is None:
            item.append(f'<@{user_id}>')
        else:
            color = user.accent_color.hex if user.accent_color else '#000000'
            span = Tag(name='span', attrs=dict(style=f'color:{color};'))
            span.append(f'@{user.display_name}#{user.discriminator}')
            item.append(span)
    for item in soup.select('discord-role'):
        role_id = item.text
        role = await guild.fetch_role(role_id)
        item.clear()
        if role is None:
            item.append(f'<@&{role_id}>')
        else:
            span = Tag(name='span', attrs=dict(style=f'color:{role.color.hex};'))
            span.append(f'@{role.name}')
            item.append(span)
    for item in soup.select('discord-channel'):
        channel_id = item.text
        channel = await guild.fetch_channel(channel_id)
        item.clear()
        if channel is None:
            item.append(f'<#{channel_id}>')
        else:
            a = Tag(name='a', attrs=dict(href=f'https://discord.com/channels/{guild.id}/{channel_id}'))
            a.append(f'#{channel.name}')
            item.append(a)
    return str(soup)
