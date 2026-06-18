import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
import json
from flask import Flask
from threading import Thread

# 🌐 Configuração Keep-Alive
app = Flask('')
@app.route('/')
def home(): return "Bot Online 24/7!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

FILE_NAME = "fila_data.json"

def carregar_dados():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f: return json.load(f)
    return {"fila": [], "ids": []}

def salvar_dados(dados):
    with open(FILE_NAME, "w") as f: json.dump(dados, f)

# --- FUNÇÃO DE ATUALIZAÇÃO FORÇADA ---
async def atualizar_todos_os_paineis():
    dados = carregar_dados()
    painel_view = PainelFilaView()
    # Percorre todas as guildas e todos os canais
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=50):
                    if message.author == bot.user and message.embeds:
                        if "🌾 FILA DA FAZENDA GOMES GIRARDI 🌾" in message.embeds[0].title:
                            await message.edit(content="||@here||", embed=painel_view.gerar_embed(), view=painel_view)
            except: continue

class LembreteFilaView(View):
    def __init__(self, canal):
        super().__init__(timeout=None)
        self.canal = canal

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="btn_entrar_lembrete")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if interaction.user.id not in dados["ids"]:
            dados["fila"].append(interaction.user.display_name)
            dados["ids"].append(interaction.user.id)
            salvar_dados(dados)
            
            await interaction.response.send_message(f"✅ {interaction.user.name}, você entrou na fila!", ephemeral=True)
            try: await interaction.message.delete()
            except: pass
            
            # Chama a função que varre os canais e atualiza o painel
            await atualizar_todos_os_paineis()
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

class PainelFilaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    def gerar_embed(self):
        dados = carregar_dados()
        embed = discord.Embed(title="🌾 FILA DA FAZENDA GOMES GIRARDI 🌾", description="Clique nos botões abaixo para gerenciar sua vaga na fila!", color=discord.Color.brand_green())
        embed.set_thumbnail(url="https://r2.fivemanage.com/W9vFnvRHli5f57dMM8AKy/FazendaGomes.png")
        if dados["fila"]:
            lista_nomes = "\n".join([f"🥇 **{nome}** *(Próximo a Ser Contratado)*" if i == 0 else f"{i+1}. {nome}" for i, nome in enumerate(dados["fila"])])
            embed.add_field(name="Jogadores na Fila", value=lista_nomes, inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(dados['fila'])}")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if interaction.user.id not in dados["ids"]:
            dados["fila"].append(interaction.user.display_name)
            dados["ids"].append(interaction.user.id)
            salvar_dados(dados)
            await self.atualizar(interaction)
        else: await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila")
    async def sair(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if interaction.user.id in dados["ids"]:
            idx = dados["ids"].index(interaction.user.id)
            dados["fila"].pop(idx); dados["ids"].pop(idx)
            salvar_dados(dados)
            await self.atualizar(interaction)
        else: await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if not dados["fila"]: return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        removido_nome = dados["fila"].pop(0)
        dados["ids"].pop(0)
        salvar_dados(dados)
        await self.atualizar(interaction)
        await interaction.followup.send(f"✅ Vaga de {removido_nome} liberada!", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    bot.add_view(LembreteFilaView(None))
    print(f"✅ {bot.user.name} online!")

@bot.event
async def on_guild_channel_create(channel):
    if "ticket-" in channel.name.lower():
        await asyncio.sleep(3)
        await channel.send("Entre na fila da Fazenda:", view=LembreteFilaView(channel))

@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    view = PainelFilaView()
    await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)

bot.run(os.environ['DISCORD_TOKEN'])
