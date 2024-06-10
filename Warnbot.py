import discord
from discord.ext import commands
import json
import os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='+', intents=intents)


user_warnings = {}


warnings_file = 'warnings.json'


unauthorized_attempts_file = 'unauthorized_attempts.json'


logs_file = 'logs.json'


def load_warnings():
    global user_warnings
    if os.path.exists(warnings_file):
        with open(warnings_file, 'r') as f:
            user_warnings = json.load(f)
    else:
        user_warnings = {}


def save_warnings():
    with open(warnings_file, 'w') as f:
        json.dump(user_warnings, f, indent=4)


def save_unauthorized_attempt(ctx, command_name, reason=None):
    attempt = {
        'user': str(ctx.author),
        'user_id': ctx.author.id,
        'command': command_name,
        'time': str(datetime.now()),
        'target': ctx.message.content.split()[1] if len(ctx.message.content.split()) > 1 else None,
        'reason': reason  
    }
    if os.path.exists(unauthorized_attempts_file):
        with open(unauthorized_attempts_file, 'r') as f:
            attempts = json.load(f)
    else:
        attempts = []
    
    attempts.append(attempt)
    with open(unauthorized_attempts_file, 'w') as f:
        json.dump(attempts, f, indent=4)


def save_log(entry):
    if os.path.exists(logs_file):
        with open(logs_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(entry)
    with open(logs_file, 'w') as f:
        json.dump(logs, f, indent=4)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} olarak giriş yaptı!')
    load_warnings()


class MissingRole(commands.CheckFailure):
    pass


def has_role(role_name):
    def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=role_name)
        if role is None:
            raise MissingRole(f"{role_name} rolüne sahip olmalısınız.")
        return True
    return commands.check(predicate)

@bot.command()
@has_role('Etkinlik Sorumlusu') 
async def warn(ctx, member: discord.Member, *, reason: str = "Sebep belirtilmemiş"):
    if member.bot:
        await ctx.send("Botları uyarılamaz.")
        return

    if str(member.id) not in user_warnings:
        user_warnings[str(member.id)] = []

    user_warnings[str(member.id)].append(reason)
    save_warnings()

    log_entry = {
        'action': 'warn',
        'admin': str(ctx.author),
        'admin_id': ctx.author.id,
        'member': str(member),
        'member_id': member.id,
        'reason': reason,  
        'time': str(datetime.now())
    }
    save_log(log_entry)

    await ctx.send(f'{member.mention} uyarıldı. Sebep: {reason}')

@warn.error
async def warn_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send("Warn komutunu kullanmak için yeterli yetkiniz yok.")
        print(f"{ctx.author} warn komutunu kullanmaya çalıştı.")
        reason = ' '.join(ctx.message.content.split()[2:]) if len(ctx.message.content.split()) > 2 else None
        save_unauthorized_attempt(ctx, "warn", reason) 
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Geçersiz bir üye belirttiniz.")
    else:
        await ctx.send("Bir hata oluştu.")
        print(f"Warn komutunda bir hata oluştu: {error}")

@bot.command(name='warnings')
@has_role('Etkinlik Sorumlusu')
async def get_warnings(ctx, member: discord.Member):
    if str(member.id) not in user_warnings or len(user_warnings[str(member.id)]) == 0:
        await ctx.send(f'{member.mention} için uyarı bulunamadı.')
    else:
        warn_list = '\n'.join([f'{idx + 1}. {warn}' for idx, warn in enumerate(user_warnings[str(member.id)])])
        await ctx.send(f'{member.mention} için uyarılar:\n{warn_list}')

@get_warnings.error
async def get_warnings_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send("Warnings komutunu kullanmak için yeterli yetkiniz yok.")
        print(f"{ctx.author} warnings komutunu kullanmaya çalıştı.")
        save_unauthorized_attempt(ctx, "warnings")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Geçersiz bir üye belirttiniz.")
    else:
        await ctx.send("Bir hata oluştu.")
        print(f"Warnings komutunda bir hata oluştu: {error}")

@bot.command()
@has_role('Etkinlik Sorumlusu')
async def clearwarnings(ctx, member: discord.Member):
    if str(member.id) not in user_warnings or len(user_warnings[str(member.id)]) == 0:
        await ctx.send(f'{member.mention} için temizlenecek uyarı yok.')
    else:
        user_warnings[str(member.id)] = []
        save_warnings()

        log_entry = {
            'action': 'clearwarnings',
            'admin': str(ctx.author),
            'admin_id': ctx.author.id,
            'member': str(member),
            'member_id': member.id,
            'time': str(datetime.now())
        }
        save_log(log_entry)

        await ctx.send(f'{member.mention} için tüm uyarılar temizlendi.')

@clearwarnings.error
async def clearwarnings_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send("Clearwarnings komutunu kullanmak için yeterli yetkiniz yok.")
        print(f"{ctx.author} clearwarnings komutunu kullanmaya çalıştı.")
        save_unauthorized_attempt(ctx, "clearwarnings")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Geçersiz bir üye belirttiniz.")
    else:
        await ctx.send("Bir hata oluştu.")
        print(f"Clearwarnings komutunda bir hata oluştu: {error}")

@bot.command()
@has_role('Etkinlik Sorumlusu')
async def delwarn(ctx, member: discord.Member, index: int):
    if str(member.id) not in user_warnings or len(user_warnings[str(member.id)]) == 0:
        await ctx.send(f'{member.mention} için uyarı bulunamadı.')
    else:
        try:
            removed_warning = user_warnings[str(member.id)].pop(index - 1)
            save_warnings()

            log_entry = {
                'action': 'delwarn',
                'admin': str(ctx.author),
                'admin_id': ctx.author.id,
                'member': str(member),
                'member_id': member.id,
                'removed_warning': removed_warning,
                'time': str(datetime.now())
            }
            save_log(log_entry)

            await ctx.send(f'{member.mention} için uyarı silindi: {removed_warning}')
        except IndexError:
            await ctx.send(f'{member.mention} için geçersiz uyarı indeksi.')

@delwarn.error
async def delwarn_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send("Delwarn komutunu kullanmak için yeterli yetkiniz yok.")
        print(f"{ctx.author} delwarn komutunu kullanmaya çalıştı.")
        save_unauthorized_attempt(ctx, "delwarn")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Geçersiz bir üye veya indeks belirttiniz.")
    else:
        await ctx.send("Bir hata oluştu.")
        print(f"Delwarn komutunda bir hata oluştu: {error}")

@bot.command()
@has_role('Etkinlik Sorumlusu')
async def logs(ctx):
    if os.path.exists(logs_file):
        with open(logs_file, 'r') as f:
            logs = json.load(f)
        logs_list = '\n'.join([f'{log["time"]}: {log["admin"]} {log["action"]} {log.get("member", "")} {log.get("reason", "")}' for log in logs])
        await ctx.send(f'Loglar:\n{logs_list}')
    else:
        await ctx.send('Hiçbir log bulunamadı.')

@bot.command()
@has_role('Etkinlik Sorumlusu')
async def denemeler(ctx):
    if os.path.exists(unauthorized_attempts_file):
        with open(unauthorized_attempts_file, 'r') as f:
            attempts = json.load(f)
        attempts_list = '\n'.join([f'{attempt["time"]}: {attempt["user"]} {attempt["command"]} komutunu {attempt.get("target", "belirtilmedi")} üzerinde kullanmaya çalıştı. Sebep: {attempt.get("reason", "belirtilmedi")}' for attempt in attempts])
        await ctx.send(f'Yetkisiz denemeler:\n{attempts_list}')
    else:
        await ctx.send('Hiçbir yetkisiz deneme bulunamadı.')

# clearwarnall komudunu kullanabilecekler
def is_allowed_user(ctx):
    allowed_users = ["", ""] # clearwarnall komudunu kullanabilecek üyelerin discord kullanıcı isimleri
    return str(ctx.author) in allowed_users

@bot.command()
@commands.check(is_allowed_user) 
async def clearwarnall(ctx):
    global user_warnings
    if len(user_warnings) == 0:
        await ctx.send('Temizlenecek uyarı bulunamadı.')
        return

    user_warnings = {}
    save_warnings()

    log_entry = {
        'action': 'clearwarnall',
        'admin': str(ctx.author),
        'admin_id': ctx.author.id,
        'time': str(datetime.now())
    }
    save_log(log_entry)

    await ctx.send('Tüm kullanıcıların uyarıları temizlendi.')

@clearwarnall.error
async def clearwarnall_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Bu komutu kullanma yetkiniz yok.")
        print(f"{ctx.author} clearwarnall komutunu kullanmaya çalıştı.")
        save_unauthorized_attempt(ctx, "clearwarnall")
    else:
        await ctx.send("Bir hata oluştu.")
        print(f"Clearwarnall komutunda bir hata oluştu: {error}")


bot.run('YOUR_TOKEN')