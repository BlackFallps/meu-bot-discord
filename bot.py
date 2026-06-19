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
ID_CANAL_PAINEL = 1477880103039144127

fila_fazenda = []
fila_ids = []

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
        
        if fila_fazenda:
            lista_formatada = []
            for i, user_id in enumerate(fila_ids):
                mention = f"<@{user_id}>"
                if i == 0:
                    lista_formatada.append(f"🥇 **{mention}** *(Próximo a Ser Contratado)*")
                else:
                    lista_formatada.append(f"{i+1}. {mention}")
            embed.add_field(name="Jogadores na Fila", value="\n".join(lista_formatada), inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila_fazenda)}")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="||@here||", embed=self.gerar_embed(), view=self)

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
                if "ticket-" in canal.name.lower():
                    canal_encontrado = canal
                    break
            if canal_encontrado:
                await canal_encontrado.send(f"{member.mention} **Sua Vaga na Fazenda Gomes Girardi foi liberada! Procure os Gerentes.**")
                await interaction.followup.send(f"✅ Vaga de {removido_nome} liberada!", ephemeral=True)

# --- Eventos ---
@bot.event
async def on_ready():
    bot.add_view(PainelFilaView())
    print(f"✅ {bot.user.name} online!")

@bot.event
async def on_guild_channel_create(channel):
    # Apenas se for um canal de ticket
    if "ticket-" in channel.name.lower():
        # Aumentamos o tempo para 10 segundos para dar tempo do Ticket Tool terminar o serviço dele
        await asyncio.sleep(10) 
        
        # Verifica no histórico dos últimos 20 itens se JÁ existe alguma mensagem 
        # (seja do Ticket Tool ou do seu bot). 
        # Se houver mensagens, significa que o ticket já foi inicializado.
        async for message in channel.history(limit=20):
            if message.id: # Se existir QUALQUER mensagem no canal, encerra a função
                return 

        canal_painel = bot.get_channel(ID_CANAL_PAINEL)
        
        if canal_painel:
            url = f"https://discord.com/channels/{channel.guild.id}/{canal_painel.id}"
            embed = discord.Embed(
                title="Fila da Fazenda Gomes Girardi",
                description="Olá Seja bem-vindo(a). Notamos que abriu uma Pasta. Para mantermos a ordem na Fazenda devido à limitação de vagas, trabalhamos com uma fila de espera. Clique no Botão Abaixo para ir direto pro Painel onde você irá entrar na fila.",
                color=discord.Color.brand_green()
            )
            # A mensagem será enviada apenas se o canal estiver vazio (sem mensagens de outros bots)
            await channel.send(embed=embed, view=BotaoLinkView(url))
@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    await ctx.message.delete()
    view = PainelFilaView()
    await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)

bot.run(os.environ['DISCORD_TOKEN'])
