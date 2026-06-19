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

# --- CONFIGURAÇÃO ---
ID_CANAL_PAINEL = 1516284994711060631
CARGOS_PERMITIDOS = [1281476884131090468, 1509877190995476610, 1281476884131090467]

fila_jogadores = []

# --- View com o botão de LINK ---
class BotaoLinkView(View):
    def __init__(self, url):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Ir para o Painel", style=discord.ButtonStyle.link, url=url))

# --- Classe do Painel ---
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
            lista_formatada = []
            for i, jogador in enumerate(fila_jogadores):
                mention = f"<@{jogador['id']}>"
                if i == 0:
                    lista_formatada.append(f"🥇 **{mention}** *(Próximo a Ser Contratado)*")
                else:
                    lista_formatada.append(f"{i+1}. {mention}")
            embed.add_field(name="Jogadores na Fila", value="\n".join(lista_formatada), inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila_jogadores)}")
        return embed

    async def atualizar(self, interaction):
        await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)
        ping = await interaction.channel.send("||@here||")
        await asyncio.sleep(0.2)
        await ping.delete()

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        # Captura o ID do canal onde o botão foi clicado (o ticket do usuário)
        canal_ticket_id = interaction.channel.id
        
        if not any(j['id'] == interaction.user.id for j in fila_jogadores):
            fila_jogadores.append({
                'id': interaction.user.id, 
                'nome': interaction.user.display_name, 
                'canal': canal_ticket_id
            })
            await self.atualizar(interaction)
            await interaction.response.send_message("✅ Você entrou na fila a partir deste canal!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        # ... (manter a verificação de cargos aqui) ...

        if not fila_jogadores:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        
        # Remove o primeiro da fila
        jogador = fila_jogadores.pop(0)
        await self.atualizar(interaction)
        
        # Tenta buscar o canal exato que foi salvo no dicionário acima
        canal_alvo = interaction.guild.get_channel(jogador['canal'])
        
        if canal_alvo:
            await canal_alvo.send(f"<@{jogador['id']}> **Sua Vaga na Fazenda Gomes Girardi foi liberada! Procure os Gerentes ou os Donos no Condado para ser contratado.**")
            await interaction.followup.send(f"✅ Vaga liberada no canal do ticket: {canal_alvo.mention}", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Erro: Não foi possível encontrar o canal do ticket deste usuário.", ephemeral=True)

# --- Eventos ---
@bot.event
async def on_guild_channel_create(channel):
    if "ticket-" in channel.name.lower():
        await asyncio.sleep(2) 
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                return 
        url = f"https://discord.com/channels/{channel.guild.id}/{ID_CANAL_PAINEL}"
        embed = discord.Embed(
            title="Fila da Fazenda Gomes Girardi",
            description="Olá Seja bem-vindo(a) Notamos que abriu uma Pasta, Para mantermos a ordem na Fazenda devido à limitação de vagas, Trabalhamos com uma fila de espera pra Ser Contratado no Condado, Clique no Botão Abaixo para ir direto pro Painel...",
            color=discord.Color.brand_green()
        )
        await channel.send(embed=embed, view=BotaoLinkView(url), delete_after=60)

@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    print(f"✅ {bot.user.name} online!")

@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    await ctx.message.delete()
    view = PainelFilaView()
    await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)

bot.run(os.environ['DISCORD_TOKEN'])
