import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
import json
from flask import Flask
from threading import Thread

# Configuração Keep-Alive
app = Flask('')
@app.route('/')
def home(): return "Bot Online 24/7!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Arquivos de persistência
DATA_FILE = "dados_fila.json"

def get_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {"fila": [], "ids": [], "painel_msg_id": None, "painel_chan_id": None}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- FUNÇÃO DE ATUALIZAÇÃO INSTANTÂNEA ---
async def atualizar_painel_imediato():
    data = get_data()
    if data["painel_msg_id"] and data["painel_chan_id"]:
        try:
            chan = bot.get_channel(data["painel_chan_id"])
            msg = await chan.fetch_message(data["painel_msg_id"])
            await msg.edit(embed=PainelFilaView().gerar_embed(), view=PainelFilaView())
        except: pass

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
            await interaction.response.send_message("✅ Registrado!", ephemeral=True)
            try: await interaction.message.delete()
            except: pass
            # Atualiza sem varrer nada
            await atualizar_painel_imediato()
        else: await interaction.response.send_message("⚠️ Já está na fila!", ephemeral=True)

class PainelFilaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    def gerar_embed(self):
        data = get_data()
        embed = discord.Embed(title="🌾 FILA DA FAZENDA GOMES GIRARDI 🌾", color=discord.Color.brand_green())
        lista = "\n".join([f"🥇 **{nome}**" if i == 0 else f"{i+1}. {nome}" for i, nome in enumerate(data["fila"])]) if data["fila"] else "*Vazia*"
        embed.add_field(name="Jogadores", value=lista)
        embed.set_footer(text=f"Total: {len(data['fila'])}")
        return embed

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        data = get_data()
        if interaction.user.id not in data["ids"]:
            data["fila"].append(interaction.user.display_name)
            data["ids"].append(interaction.user.id)
            save_data(data)
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        else: await interaction.response.send_message("Já na fila!", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    bot.add_view(LembreteFilaView(None))
    print("✅ Bot Online!")

@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    data = get_data()
    msg = await ctx.send(embed=PainelFilaView().gerar_embed(), view=PainelFilaView())
    data["painel_msg_id"] = msg.id
    data["painel_chan_id"] = ctx.channel.id
    save_data(data)
    await ctx.message.delete()

bot.run(os.environ['DISCORD_TOKEN'])
