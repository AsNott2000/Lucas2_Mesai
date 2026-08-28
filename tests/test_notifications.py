import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from services.notification_service import NotificationService
from utils.formatters import create_report_closed_shift_dm_embed, format_duration

class MockUser:
    def __init__(self, user_id=101, display_name="Personel1", allow_dm=True):
        self.id = user_id
        self.display_name = display_name
        self.name = display_name.lower()
        self.mention = f"<@{user_id}>"
        self.allow_dm = allow_dm
        self.sent_messages = []

    async def send(self, content=None, embed=None):
        if not self.allow_dm:
            raise discord.Forbidden(MagicMock(status=403), "Cannot send messages to this user")
        self.sent_messages.append({"content": content, "embed": embed})
        return MagicMock()

class MockTextChannel:
    def __init__(self, channel_id=901, name="mesai"):
        self.id = channel_id
        self.name = name
        self.sent_messages = []

    async def send(self, content=None, embed=None, delete_after=None):
        self.sent_messages.append({"content": content, "embed": embed, "delete_after": delete_after})
        return MagicMock()

class MockGuild:
    def __init__(self, guild_id=9999, name="TestGuild"):
        self.id = guild_id
        self.name = name
        self.members = {}
        self.text_channels = []

    def get_member(self, user_id):
        return self.members.get(user_id)

    async def fetch_member(self, user_id):
        m = self.members.get(user_id)
        if m:
            return m
        raise discord.NotFound(MagicMock(status=404), "Member not found")

    def get_channel(self, channel_id):
        for ch in self.text_channels:
            if ch.id == channel_id:
                return ch
        return None

class TestNotificationService(unittest.IsolatedAsyncioTestCase):
    """Genel rapor alma bildirim servisi birim testleri."""

    def test_report_closed_shift_dm_embed(self):
        """Kapanan mesai bildirim embed içeriğini doğrula."""
        embed = create_report_closed_shift_dm_embed(
            user_name="Ahmet",
            duration_seconds=3600,
            admin_name="SuperAdmin"
        )
        self.assertIn("BİLGİLENDİRMESİ", embed.title)
        self.assertIn("Ahmet", embed.description)
        self.assertIn("SuperAdmin", embed.description)
        self.assertIn("1 saat", embed.description)
        self.assertIn("Mesai Başlat", embed.description)

    async def test_notify_empty_records(self):
        """Kapatılan kayıt olmadığında servisin 0 dönmesini test et."""
        guild = MockGuild()
        bot = MagicMock()
        res = await NotificationService.notify_closed_shifts_on_report(
            bot=bot,
            guild=guild,
            closed_records=[],
            admin_name="Admin"
        )
        self.assertEqual(res["dm_sent"], 0)
        self.assertEqual(res["dm_failed"], 0)
        self.assertEqual(len(res["failed_user_ids"]), 0)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_notify_successful_dm(self, mock_sleep):
        """DM kutusu açık olan kullanıcılara başarıyla bildirim gönderildiğini test et."""
        guild = MockGuild()
        u1 = MockUser(user_id=101, display_name="Personel1", allow_dm=True)
        u2 = MockUser(user_id=102, display_name="Personel2", allow_dm=True)
        guild.members[101] = u1
        guild.members[102] = u2

        closed_records = [
            {"user_id": 101, "user_name": "Personel1", "duration_seconds": 3600},
            {"user_id": 102, "user_name": "Personel2", "duration_seconds": 7200}
        ]

        bot = MagicMock()
        res = await NotificationService.notify_closed_shifts_on_report(
            bot=bot,
            guild=guild,
            closed_records=closed_records,
            admin_name="SuperAdmin"
        )

        self.assertEqual(res["dm_sent"], 2)
        self.assertEqual(res["dm_failed"], 0)
        self.assertEqual(len(u1.sent_messages), 1)
        self.assertEqual(len(u2.sent_messages), 1)
        self.assertIn("BİLGİLENDİRMESİ", u1.sent_messages[0]["embed"].title)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("services.panel_manager.panel_manager.get_target_channel")
    async def test_notify_forbidden_dm_fallback_channel(self, mock_get_channel, mock_sleep):
        """DM'i kapalı kullanıcılar için mesai kanalında etiketli uyarı bırakıldığını test et."""
        guild = MockGuild()
        mesai_ch = MockTextChannel(channel_id=888, name="mesai")
        mock_get_channel.return_value = mesai_ch

        # u1 açık DM, u2 kapalı DM
        u1 = MockUser(user_id=201, display_name="AcikDM", allow_dm=True)
        u2 = MockUser(user_id=202, display_name="KapaliDM", allow_dm=False)
        guild.members[201] = u1
        guild.members[202] = u2

        closed_records = [
            {"user_id": 201, "user_name": "AcikDM", "duration_seconds": 1800},
            {"user_id": 202, "user_name": "KapaliDM", "duration_seconds": 5400}
        ]

        bot = MagicMock()
        res = await NotificationService.notify_closed_shifts_on_report(
            bot=bot,
            guild=guild,
            closed_records=closed_records,
            admin_name="Patron"
        )

        self.assertEqual(res["dm_sent"], 1)
        self.assertEqual(res["dm_failed"], 1)
        self.assertEqual(res["failed_user_ids"], [202])

        # u1 DM almış olmalı
        self.assertEqual(len(u1.sent_messages), 1)
        # u2 DM alamadı ama mesai kanalına toplu mesaj gitmiş olmalı
        self.assertEqual(len(mesai_ch.sent_messages), 1)
        channel_msg = mesai_ch.sent_messages[0]
        self.assertIn("<@202>", channel_msg["content"])
        self.assertIn("Mesai Başlat", channel_msg["content"])
        self.assertEqual(channel_msg["delete_after"], 90)

if __name__ == "__main__":
    unittest.main()
