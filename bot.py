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

# --- View com o botão de LINK (Para a mensagem da imagem) ---
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
            # Salva o ID do canal onde o usuário está no momento
            fila_jogadores.append({
                'id': interaction.user.id, 
                'nome': interaction.user.display_name, 
                'canal': canal_ticket_id
            })
            await self.atualizar(interaction)
            await interaction.response.send_message("✅ Você entrou na fila a partir deste ticket!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def avancar(self, interaction: discord.Interaction, button: Button):
        # 1. VERIFICAÇÃO DE CARGOS
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role_id in CARGOS_PERMITIDOS for role_id in user_roles):
            return await interaction.response.send_message(
                "❌ Apenas Gerentes ou Donos podem liberar a vaga da Fazenda!", ephemeral=True
            )

        # 2. VERIFICAÇÃO DE FILA
        if not fila_jogadores:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        
        # 3. LIBERAÇÃO DA VAGA
        jogador = fila_jogadores.pop(0)
        await self.atualizar(interaction)
        
        # Busca o canal exato que salvamos no momento que ele entrou
        canal_correto = interaction.guild.get_channel(jogador['canal'])
        
        if canal_correto:
            await canal_correto.send(f"<@{jogador['id']}> **Sua Vaga na Fazenda Gomes Girardi foi liberada, Procure os Gerentes ou os Donos no Condado Pra ser Contratado!!**")
            await interaction.followup.send(f"✅ Vaga de {jogador['nome']} liberada no canal correto!", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ Vaga liberada, mas o canal do ticket deste usuário não foi encontrado.", ephemeral=True)
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
                await canal_encontrado.send(f"{member.mention} **Sua Vaga na Fazenda Gomes Girardi foi liberado, Procure os Gerentes ou os Donos no Condado Pra ser Contratado!!**")
                await interaction.followup.send(f"Vaga de {removido_nome} liberada ✅", ephemeral=True)

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
        
        # Apenas esta linha deve existir:
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
