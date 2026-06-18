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

# --- PERSISTÊNCIA DE DADOS ---
ARQUIVO_DADOS = "fila_dados.json"

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r") as f:
            return json.load(f)
    return {"fila_fazenda": [], "fila_ids": []}

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w") as f:
        json.dump(dados, f)

# --- CLASSE DO PAINEL PRINCIPAL ---
class PainelFilaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    def gerar_embed(self):
        dados = carregar_dados()
        fila = dados["fila_fazenda"]
        embed = discord.Embed(
            title="🌾 FILA DA FAZENDA GOMES GIRARDI 🌾",
            description="Clique abaixo para gerenciar sua vaga na fila!",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url="https://r2.fivemanage.com/W9vFnvRHli5f57dMM8AKy/FazendaGomes.png")
        if fila:
            lista = "\n".join([f"🥇 **{nome}** *(Próximo a Ser Contratado)*" if i == 0 else f"{i+1}. {nome}" for i, nome in enumerate(fila)])
            embed.add_field(name="Jogadores na Fila", value=lista, inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila)}")
        return embed

    async def atualizar_painel(self, interaction):
        # Atualiza a mensagem onde o botão foi clicado
        await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)
        # Força atualização visual em outros locais se necessário
        ping = await interaction.channel.send("||@here||")
        await asyncio.sleep(0.5)
        await ping.delete()

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if interaction.user.id not in dados["fila_ids"]:
            dados["fila_fazenda"].append(interaction.user.display_name)
            dados["fila_ids"].append(interaction.user.id)
            salvar_dados(dados)
            await self.atualizar_painel(interaction)
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila")
    async def sair(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if interaction.user.id in dados["fila_ids"]:
            idx = dados["fila_ids"].index(interaction.user.id)
            dados["fila_fazenda"].pop(idx)
            dados["fila_ids"].pop(idx)
            salvar_dados(dados)
            await self.atualizar_painel(interaction)
        else:
            await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if not dados["fila_fazenda"]:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        removido_nome = dados["fila_fazenda"].pop(0)
        removido_id = dados["fila_ids"].pop(0)
        salvar_dados(dados)
        await self.atualizar_painel(interaction)
        
        member = interaction.guild.get_member(removido_id)
        if member:
            await interaction.followup.send(f"✅ Vaga de {removido_nome} liberada!", ephemeral=True)

# --- CLASSE DO LEMBRETE NO TICKET ---
class LembreteFilaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="btn_entrar_lembrete")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        dados = carregar_dados()
        if interaction.user.id not in dados["fila_ids"]:
            dados["fila_fazenda"].append(interaction.user.display_name)
            dados["fila_ids"].append(interaction.user.id)
            salvar_dados(dados)
            
            await interaction.response.send_message(f"✅ {interaction.user.name}, você entrou na fila ({interaction.channel.name})!", ephemeral=True)
            try: await interaction.message.delete()
            except: pass
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    bot.add_view(LembreteFilaView())
    print(f"✅ {bot.user.name} online!")

@bot.event
async def on_guild_channel_create(channel):
    if "ticket-" in channel.name.lower():
        await asyncio.sleep(3)
        await channel.send("Clique no botão abaixo para entrar na fila da Fazenda:", view=LembreteFilaView())

@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    await ctx.message.delete()
    view = PainelFilaView()
    await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)

bot.run(os.environ['DISCORD_TOKEN'])
