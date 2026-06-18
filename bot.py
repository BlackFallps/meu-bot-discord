import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
from flask import Flask
from threading import Thread

# 🌐 Configuração do Keep-Alive
app = Flask('')
@app.route('/')
def home(): return "Bot Online 24/7!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

fila_fazenda = []
fila_ids = []

# --- Classe do Lembrete no Ticket ---
class LembreteFilaView(View):
    def __init__(self, canal):
        super().__init__(timeout=None)
        self.canal = canal

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="btn_entrar_lembrete")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        global fila_fazenda, fila_ids
        
        if interaction.user.id not in fila_ids:
            fila_fazenda.append(interaction.user.display_name)
            fila_ids.append(interaction.user.id)
            
            await interaction.response.send_message("✅ Você entrou na fila com sucesso!", ephemeral=True)
            
            # Deleta o lembrete
            try: await interaction.message.delete()
            except: pass
            
            # ATUALIZAÇÃO DO PAINEL: Procura o painel em todos os canais e força a edição
            painel_view = PainelFilaView()
            for channel in interaction.guild.text_channels:
                async for message in channel.history(limit=50):
                    if message.author == bot.user and "🚜 FILA DA FAZENDA" in message.embeds[0].title if message.embeds else False:
                        await message.edit(content="||@here||", embed=painel_view.gerar_embed(), view=painel_view)
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

# --- Classe do Painel Principal ---
class PainelFilaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    def gerar_embed(self):
        embed = discord.Embed(
            title="🌾 FILA DA FAZENDA GOMES GIRARDI 🌾",
            description="Clique nos botões abaixo para gerenciar sua vaga na fila!",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url="https://r2.fivemanage.com/W9vFnvRHli5f57dMM8AKy/FazendaGomes.png")
        if fila_fazenda:
            lista_nomes = "\n".join([f"🥇 **{nome}** *(Próximo a Ser Contratado)*" if i == 0 else f"{i+1}. {nome}" for i, nome in enumerate(fila_fazenda)])
            embed.add_field(name="Jogadores na Fila", value=lista_nomes, inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila_fazenda)}")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)
        ping = await interaction.channel.send("||@here||")
        await asyncio.sleep(0.5)
        await ping.delete()

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in fila_ids:
            fila_fazenda.append(interaction.user.display_name)
            fila_ids.append(interaction.user.id)
            await self.atualizar(interaction)
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila")
    async def sair(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id in fila_ids:
            idx = fila_ids.index(interaction.user.id)
            fila_fazenda.pop(idx)
            fila_ids.pop(idx)
            await self.atualizar(interaction)
        else:
            await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        if not fila_fazenda:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        removido_nome = fila_fazenda.pop(0)
        removido_id = fila_ids.pop(0)
        await self.atualizar(interaction)
        member = interaction.guild.get_member(removido_id)
        if member:
            canal_encontrado = None
            for canal in interaction.guild.text_channels:
                if canal.permissions_for(member).read_messages and "ticket-" in canal.name.lower():
                    canal_encontrado = canal
                    break
            if canal_encontrado:
                await canal_encontrado.send(f"{member.mention} Sua Vaga na Fazenda Gomes Girardi foi liberada! Estamos Te Esperando No Condado...")
                await interaction.followup.send(f"✅ Vaga de {removido_nome} liberada e aviso enviado no canal {canal_encontrado.mention}!", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ Vaga de {removido_nome} liberada, mas não encontrei o canal de ticket.", ephemeral=True)

# --- Eventos ---
@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    bot.add_view(LembreteFilaView(None))
    print(f"✅ {bot.user.name} online!")

@bot.event
async def on_guild_channel_create(channel):
    if "ticket-" in channel.name.lower():
        await asyncio.sleep(3)
        embed = discord.Embed(
            title="Fila da Fazenda Gomes Girardi",
            description="Olá! Seja bem-vindo(a) Notamos que abriu uma pasta, Para mantermos a ordem na Fazenda devido à limitação de vagas, trabalhamos com uma fila de espera, Entre na fila clicando no botão abaixo, assim que chegar a sua vez, você receberá uma notificação aqui na sua pasta...",
            color=discord.Color.brand_green()
        )
        await channel.send(embed=embed, view=LembreteFilaView(channel))

@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    await ctx.message.delete()
    view = PainelFilaView()
    await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)

bot.run(os.environ['DISCORD_TOKEN'])
