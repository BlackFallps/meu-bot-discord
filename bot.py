import discord
from discord.ext import commands, tasks
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

# --- CONFIGURAÇÃO ---
ID_CANAL_PAINEL = 1516284994711060631
CARGOS_PERMITIDOS = [1281476884131090468, 1509877190995476610, 1281476884131090467]
ARQUIVO_FILA = "fila.json"

# --- LISTA E PERSISTÊNCIA ---
fila_jogadores = []

def salvar_fila():
    with open(ARQUIVO_FILA, "w") as f:
        json.dump(fila_jogadores, f)

def carregar_fila():
    global fila_jogadores
    if os.path.exists(ARQUIVO_FILA):
        try:
            with open(ARQUIVO_FILA, "r") as f:
                fila_jogadores = json.load(f)
        except:
            fila_jogadores = []

# --- TAREFA DE LEMBRETE ---
@tasks.loop(hours=72) 
async def lembrete_fatura():
    canal = bot.get_channel(1281476886232563774)
    if canal:
        # 1. Envia o ping oculto primeiro
        ping = await canal.send("||@here||")
        await asyncio.sleep(0.1) 
        await ping.delete()      
        
        # 2. Define a cor e o embed
        cor_vermelho_escuro = discord.Color.from_rgb(139, 0, 0)
        
        embed = discord.Embed(
            title="📢 EII, VOÇÊ JÁ DEIXOU TUDO ACERTADO COM A FAZENDA?",
            description=(
                "Lembre-se de Verificar sua Fatura Obrigatoria Semanal...\n\n"
                "Procure um de nossos Gerentes ou Donos no Condado o Quanto Antes, Se você Já Realizou o Pagamento, **DESCONSIDERE ESTA MENSAGEM** Agradecemos o seu Trabalho Pela Fazenda!!"
            ),
            color=cor_vermelho_escuro
        )
        
        embed.set_footer(text="© Fazenda Gomes Girardi - Administração")
        
        # 3. Envia o embed
        await canal.send(embed=embed)

@lembrete_fatura.before_loop
async def before_lembrete():
    await bot.wait_until_ready()

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
            description="Clique nos Botões Abaixo Para Gerenciar sua Vaga na Fila!",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url="https://r2.fivemanage.com/W9vFnvRHli5f57dMM8AKy/FazendaGomes.png")
        
        if fila_jogadores:
            lista_formatada = []
            for i, jogador_id in enumerate(fila_jogadores):
                mention = f"<@{jogador_id}>"
                if i == 0:
                    lista_formatada.append(f"🥇 **{mention}** *(Próximo a Ser Contratado)*")
                else:
                    lista_formatada.append(f"{i+1}. {mention}")
            embed.add_field(name="Jogadores na Fila", value="\n".join(lista_formatada), inline=False)
        else:
            embed.add_field(name="Jogadores na Fila", value="*Ninguém na Fila por Enquanto.*", inline=False)
        embed.set_footer(text=f"Total: {len(fila_jogadores)}")
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        asyncio.create_task(self.enviar_ping_temporario(interaction.channel))

    async def enviar_ping_temporario(self, channel):
        try:
            ping = await channel.send("||@here||")
            await asyncio.sleep(0.1)
            await ping.delete()
        except Exception as e:
            print(f"Erro ao processar ping: {e}")

    # --- BOTÃO: ENTRAR ---
    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="entrar_fila_novo")
    async def entrar(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in fila_jogadores:
            # Ação de entrar na fila
            fila_jogadores.append(interaction.user.id)
            salvar_fila() # <--- ADICIONADO
            
            # Edita a mensagem com a nova fila e dispara o ping
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
            asyncio.create_task(self.enviar_ping_temporario(interaction.channel))
        else:
            # Usuário já está na fila, apenas avisa sem atualizar tudo
            await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)

   # --- BOTÃO: SAIR ---
    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, custom_id="sair_fila_novo")
    async def sair(self, interaction: discord.Interaction, button: Button):
        # 1. Verifica IDs dos cargos
        cargos_usuario = [role.id for role in interaction.user.roles]
        eh_admin = interaction.user.guild_permissions.administrator
        tem_cargo = any(role_id in CARGOS_PERMITIDOS for role_id in cargos_usuario)
        
        eh_gerente = eh_admin or tem_cargo
        
        # Caso 1: O usuário está na fila (comum)
        if interaction.user.id in fila_jogadores:
            fila_jogadores.remove(interaction.user.id)
            salvar_fila() # <--- ADICIONADO
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
            asyncio.create_task(self.enviar_ping_temporario(interaction.channel))

        # Caso 2: Gerente clicou mas não está na fila -> Remove o 1º da fila
        elif eh_gerente and fila_jogadores:
            removido_id = fila_jogadores.pop(0)
            salvar_fila() # <--- ADICIONADO
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
            await interaction.followup.send(f"Você Removeu <@{removido_id}> Da Fila ✅", ephemeral=True)
            # Dispara o ping em segundo plano
            asyncio.create_task(self.enviar_ping_temporario(interaction.channel))
            
        # Caso 3: Não está na fila e não é gerente
        else:
            await interaction.response.send_message(
                f"DEBUG: Admin={eh_admin}, CargoPermitido={tem_cargo}. Você não está na fila ou não tem permissão.", 
                ephemeral=True
            )

    # --- BOTÃO: LIBERAR VAGA ---
    @discord.ui.button(label="Liberar Vaga 1° da Fila", style=discord.ButtonStyle.blurple, custom_id="liberar_vaga")
    async def liberar(self, interaction: discord.Interaction, button: Button):
        # 1. Verifica permissão
        if not any(role.id in CARGOS_PERMITIDOS for role in interaction.user.roles):
            return await interaction.response.send_message(
                "Você Não Tem Permissão! Somente Gerentes ou Donos Podem Liberar Vagas ❌", 
                ephemeral=True
            )

        if not fila_jogadores:
            return await interaction.response.send_message("A fila está vazia!", ephemeral=True)
        
        removido_id = fila_jogadores.pop(0)
        salvar_fila() # <--- ADICIONADO
        
        # 2. Resposta inicial editando o painel (Unificada)
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        
        # 3. Dispara o ping temporário em SEGUNDO PLANO
        asyncio.create_task(self.enviar_ping_temporario(interaction.channel))
    
        # 4. Envia a DM
        try:
            member = interaction.guild.get_member(removido_id)
            if member:
                await member.send(f"**Sua Vaga na Fazenda Gomes Girardi Foi Liberado!** Procure os Gerentes ou os Donos no Condado Para Ser Contratado!!")
        except:
            pass
            
        # 5. Notificação de sucesso para o Gerente
        await interaction.followup.send(f"Vaga de <@{removido_id}> Liberado Com Sucesso ✅", ephemeral=True)

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
            description="Olá Seja Bem-Vindo(a) Notamos Que Abriu Uma Pasta, Para Mantermos a Ordem na Fazenda Devido à Limitação de Vagas, Trabalhamos Com Uma Fila de Espera pra Ser Contratado no Condado, Clique no Botão Abaixo para ir direto pro Painel...",
            color=discord.Color.brand_green()
        )
        await channel.send(embed=embed, view=BotaoLinkView(url), delete_after=60)

@bot.event
async def on_ready():
    carregar_fila()
    bot.add_view(PainelFilaView())
    lembrete_fatura.start()
    print(f"✅ {bot.user.name} online!")

@bot.command()
@commands.has_permissions(administrator=True)
async def fixarpainel(ctx):
    await ctx.message.delete()
    view = PainelFilaView()
    await ctx.send(content="||@here||", embed=view.gerar_embed(), view=view)

bot.run(os.environ['DISCORD_TOKEN'])
