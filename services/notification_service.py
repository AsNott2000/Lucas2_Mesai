import asyncio
import logging
from typing import List, Dict, Any, Optional
import discord

from config import config
from services.panel_manager import panel_manager
from utils.formatters import create_report_closed_shift_dm_embed

logger = logging.getLogger("Lucas2MesaiBot.NotificationService")

class NotificationService:
    """Personel ve yönetim bildirimlerini yöneten asenkron servis."""

    @staticmethod
    async def notify_closed_shifts_on_report(
        bot: discord.Client,
        guild: discord.Guild,
        closed_records: List[Dict[str, Any]],
        admin_name: str = "Yönetici"
    ) -> Dict[str, Any]:
        """
        Genel rapor alma sırasında mesaisi otomatik kapatılan kullanıcılara
        DM yoluyla bilgilendirme gönderir. DM'i kapalı olanlar için #mesai kanalında
        toplu etiketleme uyarısı bırakır.
        
        :param bot: Discord Bot client örneği
        :param guild: İlgili Discord sunucusu
        :param closed_records: db.force_end_all_shifts tarafından dönen kapatılan mesai listesi
        :param admin_name: Raporu alan yöneticinin adı
        :return: {'dm_sent': int, 'dm_failed': int, 'failed_user_ids': List[int]}
        """
        if not closed_records:
            return {"dm_sent": 0, "dm_failed": 0, "failed_user_ids": []}

        dm_sent = 0
        dm_failed = 0
        failed_members: List[discord.Member] = []

        for record in closed_records:
            user_id = record["user_id"]
            user_name = record.get("user_name", str(user_id))
            duration_sec = record.get("duration_seconds", 0)

            member = guild.get_member(user_id)
            if not member:
                try:
                    member = await guild.fetch_member(user_id)
                except Exception:
                    member = None

            user_obj = member
            if not user_obj and bot:
                try:
                    user_obj = await bot.fetch_user(user_id)
                except Exception:
                    pass

            embed = create_report_closed_shift_dm_embed(
                user_name=user_name,
                duration_seconds=duration_sec,
                admin_name=admin_name
            )

            sent = False
            if user_obj:
                try:
                    await user_obj.send(embed=embed)
                    sent = True
                    dm_sent += 1
                    logger.info(f"Rapor mesai kapatma bildirimi DM ile iletildi: {user_name} (ID: {user_id})")
                except (discord.Forbidden, discord.HTTPException, Exception) as e:
                    logger.warning(f"DM kapalı olduğu için kullanıcıya ulaşılamadı ({user_name} - ID: {user_id}): {e}")
                    sent = False

            if not sent:
                dm_failed += 1
                if member:
                    failed_members.append(member)

            # Rate limit koruması: Her DM gönderimi arasında kısa bekleme
            await asyncio.sleep(0.35)

        # DM ile ulaşılamayan personeller varsa #mesai kanalında toplu geçici bildirim bırak
        if failed_members:
            mesai_channel = await panel_manager.get_target_channel(
                guild=guild,
                setting_key="panel_mesai_channel_id",
                config_id=config.MESAI_CHANNEL_ID,
                fallback_name="mesai"
            )
            if mesai_channel:
                try:
                    mentions = " ".join(m.mention for m in failed_members)
                    content = (
                        f"🔔 {mentions}\n"
                        f"**Bilgilendirme:** Genel dönem raporu alındığı için açık olan mesaileriniz sistem tarafından otomatik olarak "
                        f"sonlandırılmıştır. Görevinize devam ediyorsanız lütfen **'Mesai Başlat'** butonu ile yeni bir mesai başlatınız."
                    )
                    await mesai_channel.send(content=content, delete_after=90)
                    logger.info(f"#mesai kanalında {len(failed_members)} kişi için alternatif toplu bildirim bırakıldı.")
                except Exception as e:
                    logger.warning(f"#mesai kanalına alternatif bildirim bırakılırken hata: {e}")

        return {
            "dm_sent": dm_sent,
            "dm_failed": dm_failed,
            "failed_user_ids": [m.id for m in failed_members]
        }

notification_service = NotificationService()
