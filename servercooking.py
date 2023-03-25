from tkinter import Button
import discord
from discord.ext import commands
import asyncio
import datetime
import random
from io import BytesIO
from discord.enums import InteractionType

bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())
bot.remove_command("help")

@bot.event
async def on_ready(): # type: ignore
    print("起動完了")

@bot.command()
async def test(ctx):
    await ctx.send("test.ok!")

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#管理者向けのコマンド

#chat on off
@bot.command()
@commands.has_permissions(administrator=True)
async def chatoff(ctx):
    if isinstance(ctx.channel, discord.TextChannel):
        channel = ctx.channel
        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
        embed = discord.Embed(title="chatの無効化", description=f"{ctx.author.mention} が {channel.mention} のchatを無効化しました。", color=discord.Color.red())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="このコマンドはテキストチャンネルでのみ使用できます。", color=discord.Color.red())
        await ctx.send(embed=embed)

@chatoff.error
async def chatoff_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=discord.Color.red()))

@bot.command()
@commands.has_permissions(administrator=True)
async def chaton(ctx):
    if isinstance(ctx.channel, discord.TextChannel):
        channel = ctx.channel
        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
        embed = discord.Embed(title="chatの有効化", description=f"{ctx.author.mention} が {channel.mention} のchatを有効化しました。", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="このコマンドはテキストチャンネルでのみ使用できます。", color=discord.Color.red())
        await ctx.send(embed=embed)

@chaton.error
async def chaton_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=discord.Color.red()))

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#chatのクリア
@bot.command()
async def clear(ctx):
    if not ctx.author.guild_permissions.manage_channels:
        error_embed = discord.Embed(
            title="エラー",
            description=f"{ctx.author.mention} さんはこのコマンドを実行する権限がありません。",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        return

    # 確認メッセージを送信する
    message = await ctx.send(embed=discord.Embed(
        title="チャンネルのリセット",
        description=f"{ctx.channel.mention}をリセットしますか？\nリセットする場合:white_check_mark: を押してください",
        color=discord.Color.green()
    ))
    await message.add_reaction("✅")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message == message

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await message.clear_reactions()
        await message.edit(embed=discord.Embed(
            title="タイムアウト",
            description="時間内に✅が押されなかったためリセットはキャンセルされました。",
            color=discord.Color.red()
        ))
    else:
        await clear_and_recreate_channel(ctx)

async def clear_and_recreate_channel(ctx):
    if not ctx.author.guild_permissions.manage_channels:
        error_embed = discord.Embed(
            title="エラー",
            description=f"{ctx.author.mention} さんはこのコマンドを実行する権限がありません。",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        return

    # 削除するチャンネルの情報を取得する
    old_channel = ctx.channel
    category = old_channel.category
    channel_name = old_channel.name
    channel_position = old_channel.position
    channel_overwrites = old_channel.overwrites

    # チャンネルを削除する
    await old_channel.delete()

    # 同じカテゴリに同じ名前、設定でチャンネルを作成する
    new_channel = await category.create_text_channel(
        name=channel_name, position=channel_position, overwrites=channel_overwrites
    )

    # メッセージを送信する
    author_mention = ctx.author.mention
    message = f"{author_mention} がチャンネルをリセットしました"
    embed = discord.Embed(title="チャンネルのリセットに成功しました", description=message, color=discord.Color.green())
    await new_channel.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#埋め込みコマンド
@bot.command()
@commands.has_permissions(administrator=True)
async def embedded(ctx, title, *, message):
    # ファイルを添付する場合
    if ctx.message.attachments:
        file = await ctx.message.attachments[0].to_file()
        embed = discord.Embed(title=f"\u200e{title}\u200e", description=f"\n{message}", color=discord.Color.gold())
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)
    # ファイルを添付しない場合
    else:
        embed = discord.Embed(title=f"\u200e{title}\u200e", description=f"\n{message}", color=discord.Color.gold())
        await ctx.send(embed=embed)

@embedded.error
async def embedded_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(description="エラー\nこのコマンドを実行するには管理者権限が必要です。", color=discord.Color.red())
        await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#サーバー状況
@bot.command()
@commands.has_permissions(administrator=True)
async def membercount(ctx):
    category = await ctx.guild.create_category("サーバー状況", position=0)
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, connect=True)
    }
    channel = await category.create_voice_channel(f"👤参加人数｜{len(ctx.guild.members)}", overwrites=overwrites)

    async def update_member_count():
        while True:
            await channel.edit(name=f"👤参加人数｜{len(ctx.guild.members)}", reason="自動更新")
            await asyncio.sleep(30)

    bot.loop.create_task(update_member_count())

@membercount.error
async def membercount_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    category = discord.utils.get(member.guild.categories, name="サーバー状況")
    if category is not None:
        channel = discord.utils.get(category.voice_channels, name__startswith="👤参加人数｜")
        if channel is not None:
            await channel.edit(name=f"👤参加人数｜{len(member.guild.members)}", reason="新規参加者")

@bot.event
async def on_member_remove(member):
    category = discord.utils.get(member.guild.categories, name="サーバー状況")
    if category is not None:
        channel = discord.utils.get(category.voice_channels, name__startswith="👤参加人数｜")
        if channel is not None:
            await channel.edit(name=f"参加人数｜{len(member.guild.members)}", reason="退出者")
#--------------------------------------------------------------------------------------------------------------------------------------------------------
#ロールパネル
@bot.command()
@commands.has_permissions(administrator=True)
async def rollpanel(ctx, description, *roles: discord.Role):
    panel = discord.Embed(title="ロールパネル", description=description, color=0x00ff00)
    panel.add_field(name="", value="\n\n".join([f"{i+1}\u20e3 {role.mention}" for i, role in enumerate(roles)]), inline=False)
    panel.set_footer(text="※ 注意：連続してリアクションを押すとロールが付与されない場合があります。3秒ほど待ってからリアクションを押してください。")
    message = await ctx.send(embed=panel)
    for i in range(len(roles)):
        await message.add_reaction(f"{i+1}\u20e3")

    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) in [f"{i+1}\u20e3" for i in range(len(roles))]

    try:
        while True:
            reaction, user = await bot.wait_for('reaction_add', timeout=None, check=check)
            index = [f"{i+1}\u20e3" for i in range(len(roles))].index(str(reaction.emoji))
            role = roles[index]
            if role in user.roles: # type: ignore
                await user.remove_roles(role) # type: ignore
                await reaction.remove(user)
            else:
                await user.add_roles(role) # type: ignore
                await message.remove_reaction(str(reaction.emoji), user)
    except asyncio.TimeoutError:
        pass

    try:
        await ctx.message.delete()
        await message.delete()
    except:
        pass

    async def delete_messages():
        def check_message(message):
            return "rollpanel" in message.content.lower() and message.created_at > datetime.datetime.now() - datetime.timedelta(minutes=3)
        messages = await ctx.channel.history(limit=100).flatten()
        messages_to_delete = [message for message in messages if check_message(message)]
        await ctx.channel.delete_messages(messages_to_delete)

    await delete_messages()

@rollpanel.error
async def rollpanel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するための権限がありません。", color=0xff0000)
        await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#認証パネル
@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx, description, role: discord.Role):
    panel = discord.Embed(title="認証パネル", description=description, color=0x00ff00)
    panel.add_field(name="", value=f"✅{role.mention}", inline=False)
    panel.set_footer(text="※ 注意：連続してリアクションを押すとロールが付与されない場合があります。3秒ほど待ってからリアクションを押してください。")
    message = await ctx.send(embed=panel)
    await message.add_reaction("✅")

    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) == "✅"

    try:
        while True:
            reaction, user = await bot.wait_for('reaction_add', timeout=None, check=check)
            if role in user.roles: # type: ignore
                await user.remove_roles(role) # type: ignore
                await reaction.remove(user)
            else:
                await user.add_roles(role) # type: ignore
                await message.remove_reaction("✅", user)
    except asyncio.TimeoutError:
        pass

    try:
        await ctx.message.delete()
        await message.delete()
    except:
        pass

    async def delete_messages():
        def check_message(message):
            return "verify" in message.content.lower() and message.created_at > datetime.datetime.now() - datetime.timedelta(minutes=3)
        messages = await ctx.channel.history(limit=100).flatten()
        messages_to_delete = [message for message in messages if check_message(message)]
        await ctx.channel.delete_messages(messages_to_delete)

    await delete_messages()

@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するための権限がありません。", color=0xff0000)
        await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#ギブウェイ
@bot.command()
async def giveaway(ctx, prize_name, duration, winners: int):
    duration_seconds = 0
    if "s" in duration:
        duration_seconds = int(duration.replace("s", ""))
    elif "m" in duration:
        duration_seconds = int(duration.replace("m", "")) * 60
    elif "h" in duration:
        duration_seconds = int(duration.replace("h", "")) * 60 * 60
    elif "d" in duration:
        duration_seconds = int(duration.replace("d", "")) * 24 * 60 * 60

    embed = discord.Embed(title="🔊プレゼント企画のお知らせ",
                          description=f"🎉景品{prize_name}\n\n"
                                      f"👍参加希望の方はリアクションを押してください\n\n"
                                      f"👀{ctx.author.mention} がこの企画を主催しています！\n\n"
                                      f"⏱終了まであと {duration} (開催時間：{duration_seconds}秒)\n\n"
                                      f"🏆当選者数：{winners}人",
                          color=0xff0000)

    message = await ctx.send(embed=embed)

    await message.add_reaction("👍")

    await ctx.message.delete()

    await asyncio.sleep(duration_seconds)

    message = await ctx.channel.fetch_message(message.id)
    reaction = discord.utils.get(message.reactions, emoji="👍")

    users = []
    async for user in reaction.users():
        if not user.bot:
            users.append(user)

    if not users:
        embed = discord.Embed(title="🔊プレゼント企画のお知らせ",
                              description="参加者がいなかったため、プレゼント企画を中止します",
                              color=0xff0000)
        await ctx.send(embed=embed)
        return

    if winners > len(users):
        embed = discord.Embed(title="🔊プレゼント企画のお知らせ",
                              description="参加者が足りないため、プレゼント企画を中止します",
                              color=0xff0000)
        await ctx.send(embed=embed)
        return

    chosen_winners = random.sample(users, k=winners)

    winners_mention = "、".join([winner.mention for winner in chosen_winners])

    embed = discord.Embed(title="🔊当選者発表",
                          description=f"{prize_name}のプレゼント企画の当選者は{winners_mention}さんです！🎉おめでとうございます！\n\n"
                                      f"お手数ですが{ctx.author.mention}様のDMまで商品を受け取りに行ってください\n\n",
                          color=0x00ff00)
    await ctx.send(embed=embed)
#---------------------------------------------------------------
#通話ログ
@bot.command()
@commands.has_permissions(administrator=True)
async def voicelog(ctx, channel: discord.TextChannel):
    global voice_log_channel_id
    voice_log_channel_id = channel.id
    embed = discord.Embed(title="通話ログの出力先を設定しました", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)

@voicelog.error
async def voicelog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if after.channel:
            if voice_log_channel_id is not None:
                voice_log_channel = member.guild.get_channel(voice_log_channel_id)
                if voice_log_channel is not None:
                    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
                    embed = discord.Embed(title="通話参加ログ", description=f"{member.mention} が {after.channel.mention} に参加しました。\n\n{now}", color=0x00ff00)
                    if member.avatar:
                        embed.set_thumbnail(url=str(member.avatar.url))
                    await voice_log_channel.send(embed=embed)
        elif before.channel:
            if voice_log_channel_id is not None:
                voice_log_channel = member.guild.get_channel(voice_log_channel_id)
                if voice_log_channel is not None:
                    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
                    embed = discord.Embed(title="通話退出ログ", description=f"{member.mention} が {before.channel.mention} から退出しました。\n\n{now}", color=0xff0000)
                    if member.avatar:
                        embed.set_thumbnail(url=str(member.avatar.url))
                    await voice_log_channel.send(embed=embed)

#----------------------------------------------------------------------------------------
#メッセージの削除ログ
@bot.command()
@commands.has_permissions(administrator=True)
async def dellog(ctx, channel: discord.TextChannel):
    global del_log_channel_id
    del_log_channel_id = channel.id
    embed = discord.Embed(title="ログ出力先設定完了", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)

@dellog.error
async def dellog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if del_log_channel_id is not None:
        del_log_channel = message.guild.get_channel(del_log_channel_id)
        if del_log_channel is not None:
            now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
            embed = discord.Embed(title="メッセージ削除ログ", color=0xff0000)
            embed.add_field(name="チャンネル", value=message.channel.mention, inline=False)
            embed.add_field(name="時間", value=now, inline=False)
            embed.add_field(name="メッセージ送信者", value=message.author.mention, inline=False)
            embed.add_field(name="メッセージ内容", value=message.content, inline=False)
            if message.author.avatar:
                embed.set_thumbnail(url=str(message.author.avatar.url))
            await del_log_channel.send(embed=embed)

#----------------------------------------------------------------------------------------
#サーバー参加メッセージ
@bot.command()
@commands.has_permissions(administrator=True)
async def joinlog(ctx, channel: discord.TextChannel):
    global join_log_channel_id
    join_log_channel_id = channel.id
    embed = discord.Embed(title="ログ出力先設定完了", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)


@joinlog.error
async def joinlog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    if join_log_channel_id is not None:
        join_log_channel = member.guild.get_channel(join_log_channel_id)
        if join_log_channel is not None:
            await asyncio.sleep(3) # 3秒待つ
            now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
            embed = discord.Embed(title=f"{member.guild.name}へようこそ！！", color=0xff0000)
            embed.add_field(name="ユーザー", value=member.mention, inline=False)
            embed.add_field(name="時間", value=now, inline=False)
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            await join_log_channel.send(embed=embed)

#----------------------------------------------------------------------------------------
#サーバー退出メッセージ
@bot.command()
@commands.has_permissions(administrator=True)
async def leftlog(ctx, channel: discord.TextChannel):
    global left_log_channel_id
    left_log_channel_id = channel.id
    embed = discord.Embed(title="ログ出力先設定完了", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)


@leftlog.error
async def leftlog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if left_log_channel_id is not None:
        left_log_channel = member.guild.get_channel(left_log_channel_id)
        if left_log_channel is not None:
            await asyncio.sleep(3) # 3秒待つ
            now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
            embed = discord.Embed(title="さようなら", color=0xff0000)
            embed.add_field(name="ユーザー", value=member.mention, inline=False)
            embed.add_field(name="時間", value=now, inline=False)
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            await left_log_channel.send(embed=embed)

#------------------------------------------------------------------------------------------------
#匿名メッセージ送信
@bot.command()
@commands.dm_only()
async def dm(ctx, user_id: int, *, message):
    user = bot.get_user(user_id)
    if user:
        embed = discord.Embed(title="匿名メッセージ通知", description=message, color=discord.Color.gold())
        await user.send(embed=embed)
        embed_sent = discord.Embed(title="匿名メッセージ通知", description=f"ユーザーID {user_id} にメッセージを送信しました。", color=discord.Color.gold())
        await ctx.send(embed=embed_sent)
    else:
        embed_err = discord.Embed(title="匿名メッセージ通知", description=f"ユーザーID {user_id} にはメッセージを送信できませんでした。", color=discord.Color.gold())
        await ctx.send(embed=embed_err)


bot.run("MTA4NTI1ODI2ODk3MDA1Nzg3MQ.GvlqpD.srLETlHm-E3LPFHEAxZ-AjZ5CFSHY2G_Pbehlk")