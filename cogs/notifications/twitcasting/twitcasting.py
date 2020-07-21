from aiohttp import web
from discord.ext import commands
from discord import Embed
import logging
import os

from database.twitcasting.subscription import Subscription
from cogs.notifications.twitcasting.pytwitcast import TwitcastAPI
from cogs.notifications.twitcasting import constants

logger = logging.getLogger('zhenpai.notifications.twitcasting')


class Twitcasting(commands.Cog):
    """
    The Twitcasting cog allows users to search and follow users streaming on the Twitcasting platform (twitcasting.tv).

    TODO: Add admin-only privileges for subcommands (setup, clear)
    """
    def __init__(self):
        self.twitcasting = None
        self.init_api()

    def init_api(self):
        if os.path.isfile('config.py'):
            from cogs.notifications.twitcasting import config
            client_id = config.TWITCAST_CLIENT_ID
            client_secret = config.TWITCAST_CLIENT_SECRET
            access_token = config.TWITCAST_ACCESS_TOKEN
        else:
            client_id = os.environ.get(constants.TWITCAST_CLIENT_ID)
            client_secret = os.environ.get(constants.TWITCAST_CLIENT_SECRET)
            access_token = os.environ.get(constants.TWITCAST_ACCESS_TOKEN)
        self.twitcasting = TwitcastAPI(client_id=client_id, client_secret=client_secret, access_token=access_token)

    @commands.group()
    async def ntfy(self, ctx):
        pass

    @ntfy.group()
    async def tc(self, ctx):
        """
        Used to manage Twitcasting subscriptions.
        """
        if ctx.invoked_subcommand is None:
            help_text = ""
            for command in self.walk_commands():
                if not isinstance(command, commands.Group) and not command.hidden:
                    help_text += f'{command}: {command.help}\n'
            await ctx.send(f'```{help_text}```')

    @tc.error
    async def tc_error_handler(self, ctx, error):
        logger.warning('%s - %s', ctx.message.content, error)
        await ctx.send(f"{error}\nType `z!tc help` for usage details.")

    @tc.command(name='search')
    async def tc_search(self, ctx, *args):
        """
        Searches Twitcasting for up to three users that closely matches the provided query.
            Usage: z!tc search <arg1> <arg2> ...
        """
        if len(args) == 0:
            await ctx.send("Send at least one word in the search query.")
            return
        users = self.twitcasting.search_users(words=args, limit=3)
        for user in users:
            embed_dict = {
                'title': user.name,
                'url': f'https://twitcasting.tv/{user.screen_id}',
                'description': f'''ID: {user.id}
                                Screen ID: {user.screen_id}
                                Profile: {user.profile}\n''',
                'author': {'name': user.screen_id},
                'thumbnail': {'url': user.image}
            }
            await ctx.send(embed=Embed.from_dict(embed_dict))

    @tc.command(name='add')
    async def tc_add(self, ctx, twitcast_user_id: str, channel_name: str = None):
        """
        Adds subscription of the Twitcasting user to the provided text channel. If #<channel-name> is left blank,
        then the channel in which the command was sent is used instead.
            Usage: z!tc add <twitcasting-user-id> #<channel-name>(optional)
        """
        if channel_name:
            channel_id = self._get_channel_id_from_name(channel_name)
            if not channel_id:
                await ctx.send(f'Cannot find {channel_name} in {ctx.guild.name}')
                return
        else:
            channel_id = ctx.channel.id
            channel_name = f'<#{channel_id}>'

        users = self.twitcasting.search_users(words=twitcast_user_id, limit=1)
        if not users:
            await ctx.send(f'Cannot find {twitcast_user_id} on the Twitcasting platform. Enter a valid ID.')
            return
        twitcast_id = users[0].id
        twitcast_name = users[0].screen_id
        if twitcast_id != twitcast_user_id:
            await ctx.send(f'Cannot find {twitcast_user_id} on the Twitcasting platform. Enter a valid ID.')
            return
        if self.db.get_sub(ctx.author.id, channel_id, twitcast_user_id):
            await ctx.send(content=f"You are already subscribed to {twitcast_name} ({twitcast_user_id}) in {channel_name}.")
            return

        user = self.db.get_or_add_user(ctx.author.id)
        guild = self.db.get_or_add_guild(ctx.guild.id)
        channel = self.db.get_or_add_channel(channel_id)
        twitcast_user = self.db.get_or_add_twitcast_user(twitcast_user_id=twitcast_user_id, twitcast_name=twitcast_name)

        sub = Subscription(user.user_id, twitcast_user.twitcast_user_id, channel.channel_id, guild.guild_id)
        self.twitcasting.register_webhook(user_id=twitcast_user_id)
        self.db.add_sub(sub)
        await ctx.send(content=f"Subscribed to {twitcast_name} ({twitcast_user_id}) in {channel_name}.")
        self.db.commit()

    @tc.command(name='list')
    async def tc_list(self, ctx, channel_name: str = None):
        """
        Lists all Twitcasting users that this guild or text channel has subscribed to. If #<channel-name> is left blank,
        then the command will list subscriptions for the entire guild/server instead.
            Usage: z!tc list #<channel-name>(optional)
        """
        if channel_name:
            channel_id = self._get_channel_id_from_name(channel_name)
            if not channel_id:
                await ctx.send(f'Cannot find {channel_name} in {ctx.guild.name}')
                return
            subs = self.db.get_or_add_channel(channel_id).subscriptions
            title = f'All Subscriptions in {ctx.channel.name}'
        else:
            subs = self.db.get_or_add_guild(ctx.guild.id).subscriptions
            title = f'All Subscriptions in {ctx.guild.name}'

        user_embed = Embed(title=title)
        for sub in subs:
            twitcast_name = sub.twitcast_user.twitcast_name
            user_embed.add_field(name=f'{twitcast_name}',
                                 value=f"""Name: [{twitcast_name}](https://twitcasting.tv/{twitcast_name})
                                        ID: {sub.twitcast_user_id}
                                        Channel: <#{sub.channel_id}>""")
        await ctx.send(embed=user_embed)

    @tc.command(name='remove')
    async def tc_remove(self, ctx, twitcast_user_id: str, channel_name: str = None):
        """
        Removes subscription of the Twitcasting user from the text channel. If #<channel-name> is left blank,
        then the channel in which the command was sent is used instead.
            Usage: z!tc remove <twitcasting-user-id> #<channel-name>(optional)
        """
        if channel_name:
            channel_id = self._get_channel_id_from_name(channel_name)
            if not channel_id:
                await ctx.send(f'Cannot find {channel_name} in {ctx.guild.name}')
                return
        else:
            channel_id = ctx.channel.id

        sub = self.db.get_sub(user_id=ctx.author.id, channel_id=channel_id, twitcast_user_id=twitcast_user_id)
        if not sub:
            await ctx.send(f"You are not subscribed to user {twitcast_user_id} in {channel_name}.")
            return

        user_name = sub.twitcast_user.twitcast_name
        self.db.remove_sub(sub)
        twitcast_user = self.db.get_twitcast_user(twitcast_user_id)
        if not twitcast_user.subscribers:
            self.twitcasting.remove_webhook(user_id=twitcast_user_id)
            self.db.delete_twitcast_user(twitcast_user_id)
        await ctx.send(f"Unsubscribed from {user_name} ({twitcast_user_id}) in {channel_name}.")
        self.db.commit()

    @tc.command(name='clear')
    async def tc_clear(self, ctx):
        """
        Deletes any subscriptions related to the user that were created in the current server.
            Usage: z!tc clear
        """
        user = self.db.get_user(ctx.author.id)
        if not user:
            await ctx.send(f'{ctx.author.name} has not made any subscriptions.')
            return
        subs = self.db.get_user(ctx.author.id).subscriptions
        if not subs:
            await ctx.send(f'{ctx.author.name} has not made any subscriptions.')
            return
        twitcast_users = list(map(lambda sub: sub.twitcast_user, subs))
        self.db.delete_subs_by_user_and_guild(ctx.author.id, ctx.guild.id)
        if twitcast_users:
            for user in twitcast_users:
                if not user.subscribers:
                    self.db.delete_twitcast_user(user)
            await ctx.send(f"Cleared all twitcasting subscriptions by {ctx.author.name} on this server.")
            self.db.commit()
        else:
            await ctx.send(f"{ctx.author.name} has not subscribed to any user on this server.")

    @tc.command(name='clear_channel')
    async def tc_clear_channel(self, ctx, channel_name: str):
        """
        Deletes any subscriptions related to the user that were created in the current server.
            Usage: z!tc clear
        """
        channel_id = self._get_channel_id_from_name(channel_name)
        if not channel_id:
            await ctx.send(f'Cannot find {channel_name} in {ctx.guild.name}')
            return
        channel = self.db.get_channel(channel_id=channel_id)
        subs = channel.subscriptions
        twitcast_users = list(map(lambda sub: sub.twitcast_user, subs))
        self.db.delete_channel(channel)
        if twitcast_users:
            for user in twitcast_users:
                if not user.subscribers:
                    self.db.delete_twitcast_user(user)
            await ctx.send(f"Cleared {channel_name} of twitcasting subscriptions.")
            self.db.commit()
        else:
            await ctx.send(f"No subs had been added to {channel_name}. There is nothing to clear.")

    @tc.command(name='purge')
    async def tc_purge(self, ctx):
        pass

    @tc.command(hidden=True, name='update')
    async def tc_update(self, ctx):
        """
        Dev command used to update names of locally stored Twitcasting users
        """
        for i in self.db.get_or_add_user(ctx.author.id).subscriptions:
            print(i.twitcast_user)
            print(i.user)
            print(i.channel)
            print(i.guild)

    async def tc_broadcast(self, request):
        """
        Callback function that forwards incoming Twitcasting webhooks to subscribed channels.
        """
        request = await request.json()
        movie, user = self.twitcasting.parse_incoming_webhook(request)
        res = self.db.get_subs_by_twitcast_user_id(twitcast_user_id=user.id)
        message = f'{user.screen_id} has went live!' if user.is_live else f'{user.screen_id} has gone offline!'
        embed_dict = {
            'title': message,
            'description': f'**Title**: [{movie.title}]({movie.link})\n{movie.subtitle}',
            'author': {'name': user.screen_id,
                       'icon_url': user.image},
            'thumbnail': {'url': user.image}
        }
        embed = Embed.from_dict(embed_dict)
        channel_user_dict = {}
        for sub in res:
            channel_user_dict.setdefault(sub.channel_id, []).append(sub.user_id)
        for channel_id, user_ids in channel_user_dict.items():
            channel = self.bot.get_channel(int(channel_id))
            fmt_user_ids = list(map(lambda u: f'<@{u}>', user_ids))
            users_to_ping = ' '.join(fmt_user_ids)
            await channel.send(f'{message} {users_to_ping}', embed=embed)
        return web.Response(status=200)

    def _get_channel_id_from_name(self, channel_name: str):
        channel_id = channel_name.strip('<>#')
        try:
            if self.bot.get_channel(int(channel_id)):
                return channel_id
            else:
                return None
        except ValueError:
            return None
