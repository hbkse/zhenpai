from aiohttp import web
from discord.ext import commands
from discord import Embed
from discord import NotFound
import logging
import os

from .database import TwitcastDatabase, Subscription
from .pytwitcast import TwitcastAPI
from . import constants


class Twitcasting(commands.Cog):
    """
    The Twitcasting cog allows users to search and follow users streaming on the Twitcasting platform (twitcasting.tv).
    The high-level workflow of the cog is that it creates and records a Discord webhook

    TODO: Add admin-only privileges for subcommands (setup, clear)
    """
    def __init__(self, bot):
        self.logger = logging.getLogger('zhenpai.twitcasting')
        self.bot = bot
        self.twitcasting = None
        self.init_API()
        self.db = TwitcastDatabase()

    def init_API(self):
        if os.path.isfile('config.py'):
            from . import config
            client_id = config.TWITCAST_CLIENT_ID
            client_secret = config.TWITCAST_CLIENT_SECRET
            access_token = config.TWITCAST_ACCESS_TOKEN
        else:
            client_id = os.environ.get(constants.TWITCAST_CLIENT_ID)
            client_secret = os.environ.get(constants.TWITCAST_CLIENT_SECRET)
            access_token = os.environ.get(constants.TWITCAST_ACCESS_TOKEN)
        self.twitcasting = TwitcastAPI(client_id=client_id, client_secret=client_secret, access_token=access_token)

    @commands.group()
    async def tc(self, ctx):
        if ctx.invoked_subcommand is None:
            help_text = ""
            for command in self.walk_commands():
                if not isinstance(command, commands.Group) and not command.hidden:
                    help_text += f'{command}: {command.help}\n'
            await ctx.send(f'```{help_text}```')

    @tc.command()
    async def setup(self, ctx, webhook_name: str):
        """
        Sets up the text channel for twitcasting bot usage by creating a webhook with the provided name.
            Usage: z!tc setup <name-of-webhook>
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        res = self.db.get_subs_by_channel(channel_id=channel_id)
        if not res:
            webhook = await ctx.channel.create_webhook(name=webhook_name)
            self.db.add_sub(Subscription(channel_id, webhook.id, None, None))
            await ctx.send(f"""Created webhook with name {webhook_name}.""")
            self.db.commit()
        else:
            await ctx.send(f"""Text channel has already been setup with id, {res[0].webhook_id}
                            Please run z!tc rename <new-webhook-name> to point subscriptions to new webhook.""")

    @tc.command()
    async def search(self, ctx, query: str):
        """
        Searches twitcasting for up to three users that closely matches the provided query.
            Usage: z!tc search <arg1> <arg2> ...
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        res = self.db.get_subs_by_channel(channel_id=channel_id)
        if not res:
            await ctx.send("""You have not setup this channel for creating webhooks! 
                            Run ```z!tc setup <name-of-webhook>``` to create a webhook for this channel.""")
            return
        webhook_id = res[0].webhook_id
        webhook = await self.bot.fetch_webhook(webhook_id)
        users = self.twitcasting.search_users(words=query, limit=3)
        embeds = []
        for user in users:
            embed_dict = {
                'title': user.name,
                'url': f'https://twitcasting.tv/{user.screen_id}',
                'description': f'''ID: {user.id}
                                Screen ID: {user.screen_id}
                                Profile: {user.profile}\n''',
                'author': {'name': user.screen_id,
                           'icon_url': user.image},
                'thumbnail': {'url': user.image}
            }
            embeds.append(Embed.from_dict(embed_dict))
        await webhook.send(embeds=embeds)

    @tc.command()
    async def sub(self, ctx, user_id: str):
        """
        Subscribes the text channel to the provided twitcasting user id.
            Usage: z!tc sub <twitcasting-user-id>
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        res = self.db.get_subs_by_channel(channel_id=channel_id)
        if not res:
            await ctx.send("""You have not setup this channel for creating webhooks! 
                    Run ```z!tc setup <name-of-webhook>``` to create a webhook for this channel.""")
            return
        webhook_id = res[0].webhook_id
        users = self.twitcasting.search_users(words=user_id, limit=1)
        assert(users[0].id == user_id)
        self.twitcasting.register_webhook(user_id=user_id)
        self.db.add_sub(Subscription(channel_id, webhook_id, user_id, users[0].screen_id))
        await ctx.send(content=f"Added {users[0].screen_id} ({user_id}) to list of webhooks!")
        self.db.commit()

    @tc.command()
    async def list(self, ctx):
        """
        Lists all twitcasting users that this text channel has subscribed to.
            Usage: z!tc list
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        users = self.db.get_subs_by_channel(channel_id=channel_id)
        user_embed = Embed(title='Registered Users')
        for user in users:
            if user.twitcast_user_id:
                user_embed.add_field(name=user.twitcast_name,
                                     value=f'ID: {user.twitcast_user_id}',
                                     inline=False)
        await ctx.send(embed=user_embed)

    @tc.command()
    async def remove(self, ctx, user_id: str):
        """
        Removes subscription to the provided twitcasting user id.
            Usage: z!tc remove <twitcasting-user-id>
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        self.db.remove_sub_from_channel_by_user_id(channel_id=channel_id, twitcast_user_id=user_id)
        if self.db.count_subs_by_user_id(twitcast_user_id=user_id) == 0:
            self.twitcasting.remove_webhook(user_id=user_id)
        await ctx.send(f"Deleted user {user_id} from list of webhooks.")
        self.db.commit()

    @tc.command()
    async def rename(self, ctx, webhook_name: str):
        """
        Migrates subscriptions to a new webhook with the provided name. Deletes the previous webhook.
            Usage: z!tc rename <new-webhook-name>
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        res = self.db.get_subs_by_channel(channel_id=channel_id)
        if res:
            webhook_id = res[0].webhook_id
            try:
                webhook = await self.bot.fetch_webhook(webhook_id)
                await webhook.delete()
            except NotFound:
                self.logger.warning("Could not find and delete previously stored webhook with id %s", webhook_id)
            new_webhook = await ctx.channel.create_webhook(name=webhook_name)
            self.db.update_webhook_id_of_channel(channel_id=channel_id, webhook_id=new_webhook.id)
            await ctx.send(f"Updated webhook with name {webhook_name}.")
            self.db.commit()
        else:
            await ctx.send(f"""Text channel has not been setup with a webhook.
                            Please run z!tc setup <name-of-webhook> to start using the z!tc bot.""")

    @tc.command()
    async def clear(self, ctx):
        """
        Clears the text channel of the webhook created by the twitcasting bot. Deletes any subscriptions added in this text channel.
            Usage: z!tc clear
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        res = self.db.get_subs_by_channel(channel_id=channel_id)
        if res:
            webhook_id = res[0].webhook_id
            try:
                self.db.remove_all_subs_from_channel(channel_id=channel_id)
                webhook = await self.bot.fetch_webhook(webhook_id)
                await webhook.delete()
                await ctx.send(f"""Cleared text channel of twitcasting subscriptions and webhook.""")
                self.db.commit()
            except NotFound:
                self.logger.warning("Could not find and delete previously stored webhook with id %s", webhook_id)
        else:
            await ctx.send(f"""Text channel has not been setup with a webhook.
                            Could not clear the text channel of any bot artifacts (if any).""")

    @tc.command(hidden=True)
    async def update(self, ctx):
        """
        Dev command used to update names of locally stored Twitcasting users
        """
        channel_id = f'{ctx.guild.id}:{ctx.channel.id}'
        users = self.db.get_subs_by_channel(channel_id=channel_id)
        for user in users:
            if user.twitcast_user_id:
                new_user_info = self.twitcasting.search_users(words=user.twitcast_user_id, limit=1)
                self.db.update_name_of_twitcast_user(twitcast_user_id=user.twitcast_user_id, twitcast_name=new_user_info[0].screen_id)
        self.db.commit()

    async def broadcast(self, request):
        """
        Callback function that forwards incoming Twitcasting webhooks to subscribed channels.
        """
        request = await request.json()
        movie, user = self.twitcasting.parse_incoming_webhook(request)
        res = self.db.get_subs_by_user_id(twitcast_user_id=user.id)
        message = f'{user.screen_id} has went live!' if user.is_live else f'{user.screen_id} has gone offline!'
        embed_dict = {
            'title': message,
            'description': f'**Title**: [{movie.title}]({movie.link})\n{movie.subtitle}',
            'author': {'name': user.screen_id,
                       'icon_url': user.image},
            'thumbnail': {'url': user.image}
        }
        embed = Embed.from_dict(embed_dict)
        for row in res:
            webhook_id = row.webhook_id
            webhook = await self.bot.fetch_webhook(webhook_id=webhook_id)
            await webhook.send(embed=embed, avatar_url=user.image)
        return web.Response(status=200)
