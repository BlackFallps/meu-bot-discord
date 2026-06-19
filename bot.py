import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
from flask import Flask
from threading import Thread

# 🌐 Keep-Alive
app = Flask('')
@app.route('/')
def home(): return "Bot Online!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURAÇÃO ---
ID_CANAL_PAINEL = 1516284994711060631
# Insira aqui os IDs dos cargos que podem liberar a vaga
CARGOS_PERMITIDOS = [1281476884131090468, 1509877190995476610, 1281476884131090467]

fila_jogadores = []

class BotaoLinkView(View):
    def __init__(self, url):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Ir para o Painel", style=discord.ButtonStyle.link, url=url))

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
        
        if fila_jogadores:
            lista = [f"{i+1}. <@{j['id']}>" for i, j in enumerate(fila_jogadores)]
            embed.add_field(name="Jogadores na Fila", value="\n".join(lista), inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila_jogadores)}")
        return embed

    async def atualizar(self, interaction):
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        if not any(j['id'] == interaction.user.id for j in fila_jogadores):
            fila_jogadores.append({'id': interaction.user.id, 'canal': interaction.channel.id})
            await self.atualizar(interaction)
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila")
    async def sair(self, interaction: discord.Interaction, button: Button):
        jogador = next((j for j in fila_jogadores if j['id'] == interaction.user.id), None)
        if jogador:
            fila_jogadores.remove(jogador)
            await self.atualizar(interaction)
        else:
            await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        if not any(role.id in CARGOS_PERMITIDOS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Apenas Gerentes ou Donos podem liberar a vaga!", ephemeral=True)
        
        if not fila_jogadores:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        
        jogador = fila_jogadores.pop(0)
        await self.atualizar(interaction)
        
        canal = interaction.guild.get_channel(jogador['canal'])
        if canal:
            await canal.send(f"<@{jogador['id']}> **Sua vaga na Fazenda Gomes Girardi foi liberada!**")
            await interaction.followup.send("✅ Vaga liberada no canal do ticket!", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Erro: Não foi possível encontrar o canal original do ticket.", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    print("✅ Bot online!")

bot.run(os.environ['DISCORD_TOKEN'])
