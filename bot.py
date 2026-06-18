import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
import json
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

# --- SISTEMA DE PERSISTÊNCIA ---
DATA_FILE = "dados_fila.json"

def get_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: pass
    return {"fila": [], "ids": [], "painel_msg_id": None, "painel_chan_id": None}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- FUNÇÃO DE ATUALIZAÇÃO INSTANTÂNEA ---
async def atualizar_painel_imediato():
    data = get_data()
    if data["painel_msg_id"] and data["painel_chan_id"]:
        try:
            chan = bot.get_channel(data["painel_chan_id"])
            if chan:
                msg = await chan.fetch_message(data["painel_msg_id"])
                await msg.edit(content="||@here||", embed=PainelFilaView().gerar_embed(), view=PainelFilaView())
        except: pass

# --- Classe do Lembrete no Ticket ---
class LembreteFilaView(View):
    def __init__(self, canal):
        super().__init__(timeout=None)
        self.canal = canal

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="btn_entrar_lembrete")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        data = get_data()
        if interaction.user.id not in data["ids"]:
            data["fila"].append(interaction.user.display_name)
            data["ids"].append(interaction.user.id)
            save_data(data)
            await interaction.response.send_message("✅ Você entrou na fila com sucesso!", ephemeral=True)
            try: await interaction.message.delete()
            except: pass
            await atualizar_painel_imediato()
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

# --- Classe do Painel Principal ---
class PainelFilaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    def gerar_embed(self):
        data = get_data()
        embed = discord.Embed(
            title="🌾 FILA DA FAZENDA GOMES GIRARDI 🌾",
            description="Clique nos botões abaixo para gerenciar sua vaga na fila!",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url="https://r2.fivemanage.com/W9vFnvRHli5f57dMM8AKy/FazendaGomes.png")
        if data["fila"]:
            lista_nomes = "\n".join([f"🥇 **{nome}** *(Próximo a Ser Contratado)*" if i == 0 else f"{i+1}. {nome}" for i, nome in enumerate(data["fila"])])
            embed.add_field(name="Jogadores na Fila", value=lista_nomes, inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(data['fila'])}")
        return embed

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        data = get_data()
        if interaction.user.id not in data["ids"]:
            data["fila"].append(interaction.user.display_name)
            data["ids"].append(interaction.user.id)
            save_data(data)
            await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)
        else: await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila")
    async def sair(self, interaction: discord.Interaction, button: Button):
        data = get_data()
        if interaction.user.id in data["ids"]:
            idx = data["ids"].index(interaction.user.id)
            data["fila"].pop(idx); data["ids"].pop(idx)
            save_data(data)
            await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)
        else: await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        data = get_data()
        if not data["fila"]: return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        removido_nome = data["fila"].pop(0); data["ids"].pop(0)
        save_data(data)
        await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)
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
    data = get_data()
    await ctx.message.delete()
    view = PainelFilaView()
    msg = await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)
    data["painel_msg_id"] = msg.id
    data["painel_chan_id"] = ctx.channel.id
    save_data(data)

bot.run(os.environ['DISCORD_TOKEN'])
