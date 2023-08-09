import discord
from discord import ui
from discord.ext import menus

class MyMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None

    async def start(self, ctx, *, channel=None, wait=False):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.ctx.author

    # This is extremely similar to Custom MenuPages(I will not explain these)
    @ui.button(emoji='<:before_fast_check:754948796139569224>', style=discord.ButtonStyle.blurple)
    async def first_page(self, button, interaction):
        await self.show_page(0)

    @ui.button(emoji='<:before_check:754948796487565332>', style=discord.ButtonStyle.blurple)
    async def before_page(self, button, interaction):
        await self.show_checked_page(self.current_page - 1)

    @ui.button(emoji='<:stop_check:754948796365930517>', style=discord.ButtonStyle.blurple)
    async def stop_page(self, button, interaction):
        self.stop()

    @ui.button(emoji='<:next_check:754948796361736213>', style=discord.ButtonStyle.blurple)
    async def next_page(self, button, interaction):
        await self.show_checked_page(self.current_page + 1)

    @ui.button(emoji='<:next_fast_check:754948796391227442>', style=discord.ButtonStyle.blurple)
    async def last_page(self, button, interaction):
        await self.show_page(self._source.get_max_pages() - 1)


@bot.command()
async def your_command(ctx):
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    formatter = MySource(data, per_page=1) # MySource came from Custom MenuPages subtopic. [Please refer to that]
    menu = MyMenuPages(formatter)
    await menu.start(ctx)