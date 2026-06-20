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
CARGOS_PERMITIDOS = [1465117225672249487, 1509877190995476610, 1281476884131090467]

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
            for i, jogador_id in enumerate(fila_jogadores):
                # Aqui está a correção: usamos o jogador_id diretamente
                mention = f"<@{jogador_id}>"
                if i == 0:
                    lista_formatada.append(f"🥇 **{mention}** *(Próximo a Ser Contratado)*")
                else:
                    lista_formatada.append(f"{i+1}. {mention}")
            embed.add_field(name="Jogadores na Fila", value="\n".join(lista_formatada), inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na fila por enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila_jogadores)}")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        # Edita o painel sem causar erro de "Interação falhou"
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        # Envia o ping em segundo plano
        asyncio.create_task(self.enviar_ping_temporario(interaction.channel))

    async def enviar_ping_temporario(self, channel):
        try:
            ping = await channel.send("||@here||")
            await asyncio.sleep(0.1)
            await ping.delete()
        except Exception:
            pass

    async def enviar_ping_temporario(self, channel):
        try:
            # Envia o ping
            ping = await channel.send("||@here||")
            # Espera um pouco para a notificação ser disparada
            await asyncio.sleep(0.5)
            # Deleta a mensagem
            await ping.delete()
        except Exception as e:
            print(f"Erro ao processar ping: {e}")

    # --- BOTÃO: ENTRAR ---
    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in fila_jogadores:
            fila_jogadores.append(interaction.user.id)
            
            # 1. Edita a mensagem do painel
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
            
            # 2. Dispara o ping temporário em segundo plano
            # Usamos o canal da interação para enviar o @here
            asyncio.create_task(self.enviar_ping_temporario(interaction.channel))
            
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    # --- BOTÃO: SAIR ---
    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila")
    async def sair(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id in fila_jogadores:
            fila_jogadores.remove(interaction.user.id)
            await self.atualizar(interaction)
            # A linha de send_message foi removida
        else:
            await interaction.response.send_message("Você não está na fila.", ephemeral=True)

    # --- BOTÃO: LIBERAR VAGA ---
    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def liberar(self, interaction: discord.Interaction, button: Button):
        # 1. Verifica se tem alguém na fila
        if not fila_jogadores:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        
        # 2. Pega o ID do jogador e remove da fila
        removido_id = fila_jogadores.pop(0)
        
        # 3. Atualiza o painel primeiro (usando edit_message para responder a interação)
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        
        # 4. Tenta enviar DM para o jogador
        try:
            member = interaction.guild.get_member(removido_id)
            if member:
                await member.send(f"**Sua Vaga na Fazenda Gomes Girardi Foi Liberado!** Procure os Gerentes ou os Donos no Condado Para Ser Contratado!!")
        except discord.Forbidden:
            print("Não foi possível enviar DM (o usuário bloqueou DMs ou não é do servidor).")
            
        # 5. Envia a mensagem de confirmação para o gerente no canal (usando follow-up)
        await interaction.followup.send(f"Vaga de <@{removido_id}> liberada com sucesso! ✅", ephemeral=True)
            
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
