import json
import string

from aiohttp.client import request
from interactions import (
    Button,
    ButtonStyle,
    component_callback,
    Embed,
    EmbedField,
    ComponentContext,
    Extension,
    StringSelectMenu,
    StringSelectOption,
    InteractionContext,
    OptionType,
    SlashCommandOption,
    listen,
    slash_command,
)
from interactions.api.events import Component
from client import CustomClient

# region constants
FC = 'EswBCowBQUVzN2pOUjJsRGNYaWdOZm9HN19ocUVQdFdjMjVTVGtMbTdEV1V5aTZqOUNHQ1JPRDhzTDF5cVhCbkpVc1dyMGNBcFVfeE5LNjFUNnJVQ2RlUlpzMThZLWktSk14NjlPWTh6ZEo4NWVuODUtZGduU2FwekJUaFRkcmNTNUdlRWVodFZoa3pUNWdia0cSF0hhR0ZaSW5wTHRDT3VyOFByT2k1NEFFGiJBTy0wcmw1ZkJlVjlCbm5NVklRcTRTWDJiYmZydUpUTUxn'
FMT = 'term:%s,corpus:en-US,hhdr:true,hwdgt:true,wfp:true,ttl:,tsl:,ptl:,htror:false,_id:fc_1'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
# endregion constants

PARAMS = {'fc': FC, 'fcv': '3'}
HEADERS = {
    'User-Agent': UA,
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
}


class DefinitionError(Exception):
    pass


class NotFoundError(DefinitionError):
    pass


class RateLimitError(DefinitionError):
    pass


class UnknownError(DefinitionError):
    pass


def _parse_definition(sense, _sub=True):
    examples = []
    for example_group in sense.get('example_groups', []):
        examples.extend(example_group['examples'])
    subdefinitions = []
    for subsense in sense.get('subsenses', []):
        subdefinitions.append(_parse_definition(subsense, _sub=False))
    dsynonyms = []
    dantonyms = []
    for thesaurus in sense.get('thesaurus_entries', []):
        for synonyms in thesaurus.get('synonyms', []):
            dsynonyms.extend([s['nym'] for s in synonyms['nyms']])
        for antonyms in thesaurus.get('antonyms', []):
            dantonyms.extend([s['nym'] for s in antonyms['nyms']])
    ret = {
        'definition': sense['definition']['text'],
        'example': examples[0] if examples else None,
        'examples': examples,
        'synonyms': dsynonyms,
        'antonyms': dantonyms,
        'labels': sense.get('label_set', {}),
        'topics': [t['name'] for t in sense.get('relevant_topics', [])],
    }
    if _sub:
        ret['subdefinitions'] = subdefinitions
    return ret


async def fetch_definitions(word: str):
    params = PARAMS.copy()
    params['async'] = FMT % word
    async with request(
        'GET',
        'https://www.google.com/async/callback:5493',
        params=params,
        headers=HEADERS,
    ) as resp:
        if resp.status == 404:
            raise NotFoundError('Google returned 404 Not Found')
        if resp.status == 429:
            raise RateLimitError()
        if resp.status != 200:
            raise NotFoundError('Google returned error status %d' % resp.status)
        text = await resp.text()
    data = json.loads(text[5:])
    if (
        'feature-callback' not in data
        or 'payload' not in data['feature-callback']
        or 'single_results' not in data['feature-callback']['payload']
    ):
        raise UnknownError(data)
    data = data['feature-callback']['payload']['single_results']
    if not data:
        raise NotFoundError('No data returned from Google')
    entries = []
    for obj in data:
        if 'widget' in obj and 'error' in obj['widget']:
            error = obj['widget']['error']
            if error == 'TERM_NOT_FOUND_ERROR':
                raise NotFoundError('No definition found on Google')
            raise UnknownError(error)
        if 'entry' in obj:
            entry = obj['entry']
            if 'subentries' in entry:
                for subentry in entry['subentries']:
                    subentry['headword'] = entry['headword']
                    subentry['__subentry'] = True
                    if 'sense_family' in subentry and 'sense_families' not in subentry:
                        subentry['sense_families'] = [subentry['sense_family']]
                    if 'phonetics' not in subentry:
                        subentry['phonetics'] = entry.get('phonetics', [])
                    if 'etymology' not in subentry:
                        subentry['etymology'] = entry.get('etymology', {})
                    if 'parts_of_speech' not in subentry:
                        subentry['parts_of_speech'] = entry.get('parts_of_speech')
                    for sense_family in subentry['sense_families']:
                        if not sense_family.get('parts_of_speech'):
                            sense_family['parts_of_speech'] = sense_family['senses'][
                                0
                            ].get('parts_of_speech', [])
                    entries.append(subentry)
            else:
                entries.append(obj['entry'])
    result = []
    for entry in entries:
        entry_result = []
        for sense_family in entry['sense_families']:
            posl = sense_family.get('parts_of_speech')
            if not posl:
                posl = sense_family['senses'][0].get('parts_of_speech', [])
            if entry.get('__subentry'):
                posl = [{'value': 'phrase of *%s*' % entry['headword']}]
            if not posl:
                raise UnknownError('Cannot parse POS: %r' % sense_family)
            pos = posl[0]['value']
            definitions = []
            for sense in sense_family['senses']:
                definitions.append(_parse_definition(sense))
            forms = []
            for morph in sense_family.get('morph_units', []):
                forms.append(
                    {
                        'name': morph['form_type']['description'],
                        'pos': morph['form_type']['pos_tag'],
                        'form': morph['word_form'],
                    }
                )
            entry_result.append(
                {
                    'partOfSpeech': pos,
                    'definitions': definitions,
                    'topics': [
                        t['name'] for t in sense_family.get('relevant_topics', [])
                    ],
                    'forms': forms,
                }
            )
        res = {
            'index': entry.get('homograph_index'),
            'word': entry.get('lemma') or entry.get('headword') or word,
            'phonetic': None,
            'phonetics': [],
            'origin': entry.get('etymology', {}).get('etymology', {}).get('text'),
            'originImages': entry.get('etymology', {}).get('images', {}),
            'meanings': entry_result,
            'topics': [t['name'] for t in entry.get('term_topics', [])],
        }
        for phonetic in entry.get('phonetics', []):
            if res['phonetic'] is None:
                res['phonetic'] = phonetic.get('text')
            res['phonetics'].append(
                {'text': phonetic.get('text'), 'audio': phonetic.get('oxford_audio')}
            )
        result.append(res)
    return result


class DefineCommandExtension(Extension):
    bot: CustomClient

    async def get_definition_elements(self, word: str, page: int = 1) -> dict:
        try:
            entries = await fetch_definitions(word)
        except NotFoundError as exc:
            return {
                'content': 'Definition: **%s**\nWord not found: %s'
                % (word, exc.args[0])
            }
        except DefinitionError as exc:
            return {
                'content': 'Definition: **%s**\nError occurred:\n```\n%r\n```'
                % (word, exc)
            }
        pages = len(entries)
        data = entries[page - 1]
        embed = Embed()
        embed.title = data['word']
        desc = ''
        if data.get('phonetic'):
            desc += 'Pronounciation: *%s*\n' % data['phonetic']
        # if data.get('origin'):
        #     desc += 'Word origin: %s' % (
        #         data['origin']
        #         .replace('<i>', '*')
        #         .replace('</i>', '*')
        #         .replace('<b>', '**')
        #         .replace('</b>', '**')
        #     )
        embed.description = desc.strip()
        fields = []
        for meaning in data['meanings']:
            pos = meaning['partOfSpeech']
            text = ''
            if meaning.get('forms'):
                forms = []
                for form in meaning['forms']:
                    forms.append('%s: **%s**' % (form['name'], form['form']))
                text += '*'
                text += '; '.join(forms)
                text += '*\n'
            if meaning.get('topics'):
                text += '*Topics: '
                text += ', '.join(meaning['topics'])
                text += '*\n'
            fields.append(EmbedField(pos, text.strip() or ' '))
            for i, definition in enumerate(meaning['definitions']):
                title = ''
                if len(meaning['definitions']) > 1:
                    title += '%d. ' % (i + 1)
                if definition.get('labels'):
                    title += '*('
                    lst = []
                    for category, labels in definition['labels'].items():
                        for label in labels:
                            lst.append('%s:%s' % (category, label.lower()))
                    title += ', '.join(lst)
                    title += ')* '
                title += definition['definition']
                text = ''
                if definition.get('example'):
                    text += '> *'
                    text += definition['example']
                    text += '*\n'
                if definition.get('synonyms'):
                    text += '**Synonyms**: '
                    text += ', '.join(definition['synonyms'][:5])
                    text += '\n'
                if definition.get('antonyms'):
                    text += '**Antonyms**: '
                    text += ', '.join(definition['antonyms'][:5])
                    text += '\n'
                fields.append(EmbedField(title, text.strip() or ' '))
        embed.fields = fields
        last_page = Button(
            style=ButtonStyle.SECONDARY,
            label='Previous',
            emoji=':arrow_backward:',
            custom_id='def_p%d' % (page - 1),
            disabled=page <= 1,
        )
        next_page = Button(
            style=ButtonStyle.SECONDARY,
            label='Next',
            emoji=':arrow_forward:',
            custom_id='def_p%d' % (page + 1),
            disabled=page >= pages,
        )
        goto_page = StringSelectMenu(
            *(
                StringSelectOption(label='Page %d' % i, value=str(i))
                for i in range(1, pages + 1)
            ),
            placeholder='Go to page...',
            custom_id='def_goto'
        )
        content = 'Definition: **%s**\nPage **%d** of **%d**' % (word, page, pages)
        return {
            'content': content,
            'embeds': embed,
            'components': [[last_page, next_page], [goto_page]],
        }

    @slash_command(
        'define',
        description='Look up a word in Google Dictionary',
        options=[
            SlashCommandOption(
                'word',
                type=OptionType.STRING,
                description='The word or phrase to define',
            ),
            SlashCommandOption(
                'ephemeral',
                type=OptionType.BOOLEAN,
                description='Whether the result should be sent to only you '
                '(default everyone)',
                required=False,
            ),
            SlashCommandOption(
                'page',
                type=OptionType.INTEGER,
                description='The page to open',
                required=False,
            ),
        ],
    )
    async def define_command(self, ctx: InteractionContext):
        word: str = ctx.kwargs['word']
        ephemeral: bool = ctx.kwargs.get('ephemeral', False)
        page: int = ctx.kwargs.get('page', 1)
        if any(c not in string.ascii_letters + '1234567890-. ' for c in word):
            return await ctx.send(
                'Invalid characters, please only send words or phrases!', ephemeral=True
            )
        await ctx.defer(ephemeral=ephemeral)
        await ctx.send(**await self.get_definition_elements(word, page=page))

    @listen()
    async def on_define_component(self, event: Component):
        ctx = event.ctx
        if not ctx.custom_id.startswith('def_'):
            return
        message = ctx.message
        assert message
        if ctx.custom_id.startswith('def_p'):
            page = int(ctx.custom_id[5:])
            content = message.content
            assert content.startswith('Definition: **')
            fragment = content[14:]
            word = fragment[: fragment.index('**')]
            await ctx.defer(edit_origin=True)
            await ctx.edit_origin(**await self.get_definition_elements(word, page=page))

    @component_callback('def_goto')
    async def on_goto_component(self, ctx: ComponentContext):
        message = ctx.message
        assert message
        page = int(ctx.values[0])
        content = message.content
        assert content.startswith('Definition: **')
        fragment = content[14:]
        word = fragment[: fragment.index('**')]
        await ctx.defer(edit_origin=True)
        await ctx.edit_origin(**await self.get_definition_elements(word, page=page))


def setup(bot: CustomClient):
    DefineCommandExtension(bot)
