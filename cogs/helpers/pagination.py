import discord
from discord.ext import commands
from discord.ui import Button, View
from typing import Dict, Union, List


class Paginator(View):
    def __init__(self, ctx: commands.Context, items: List[str], title: str, items_per_page: int = 10, ephemeral: bool = True):
        super().__init__()
        self.ctx: commands.Context = ctx
        self.items: List[str] = items # should make this like Sequence[str] or something
        self.title: str = title
        self.items_per_page: int = items_per_page
        self.current_page: int = 0
        self.message: Union[discord.Embed, None] = None
        self.ephermal: bool = ephemeral

    def _get_max_pages(self):
        return len(self.items) // self.items_per_page + 1

    def _form_page(self):
        item_slice = self.items[self.current_page * self.items_per_page : (self.current_page + 1) * self.items_per_page]
        embed = discord.Embed(title=self.title)
        embed.set_footer(text=f"Page {self.current_page + 1} of {self._get_max_pages()}")
        # current formatting is just one entry and new lines, could revisit this once I have other things to paginate
        items = "\n".join(item_slice)
        embed.add_field(name="", value=items)
        return embed
    
    def _update_buttons(self):
        if self.current_page <= 0:
            self.remove_item(self.prev_button)
        elif self.prev_button not in self.children:
            self.add_item(self.prev_button)

        if self.current_page >= self._get_max_pages() - 1:
            self.remove_item(self.next_button)
        elif self.next_button not in self.children:
            self.add_item(self.next_button)

    async def show(self):
        """ Main function to show the current page of the paginator """
        embed = self._form_page()
        self._update_buttons()
        if self.message:
            await self.message.edit(embed=embed)
        else:
            self.message = await self.ctx.send(embed=embed, view=self, ephemeral=self.ephermal)
        
    async def on_timeout(self):
        if self.message:
            await self.message.delete()
            self.stop()

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.show()
        await interaction.response.defer()

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page < self._get_max_pages() - 1:
            self.current_page += 1
            await self.show()
        await interaction.response.defer()

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.primary)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.message.delete()
        self.stop()