import discord
from config import config

def has_admin_permission(user: discord.User | discord.Member) -> bool:
    """Kullanıcının yönetici yetkisi veya belirlenen admin rolüne sahip olup olmadığını doğrular."""
    if not isinstance(user, discord.Member):
        return False

    # 1. Guild Sahibi kontrolü
    if user.guild.owner_id == user.id:
        return True

    # 2. Administrator yetkisi kontrolü
    if user.guild_permissions.administrator:
        return True

    # 3. .env üzerinden tanımlanan ADMIN_ROLE_ID kontrolü
    if config.ADMIN_ROLE_ID:
        if any(role.id == config.ADMIN_ROLE_ID for role in user.roles):
            return True

    return False
