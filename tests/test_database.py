import asyncio
import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from database.db_manager import DatabaseManager
from utils.formatters import format_duration, get_discord_timestamp, to_unix_timestamp

class TestDatabaseAndLogic(unittest.IsolatedAsyncioTestCase):
    """Veritabanı ve iş mantığı birim testleri."""

    async def asyncSetUp(self):
        self.test_dir = "tests/temp_data"
        self.test_db_path = os.path.join(self.test_dir, "test_mesai.db")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db = DatabaseManager(db_path=self.test_db_path)
        await self.db.init_db()

    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_start_and_conflict_shift(self):
        """Mesai başlatma ve çakışan mesai engelleme testi."""
        guild_id = 9999
        user_id = 12345
        user_name = "TestUser"
        start_time = datetime(2026, 8, 27, 8, 0, 0, tzinfo=timezone.utc)

        # 1. İlk mesaiyi başlat
        success, shift, msg = await self.db.start_shift(guild_id, user_id, user_name, start_time)
        self.assertTrue(success)
        self.assertIsNotNone(shift)
        self.assertEqual(shift["status"], "ACTIVE")
        self.assertEqual(shift["user_id"], user_id)

        # 2. İkinci mesaiyi başlatmayı dene (Hata vermeli)
        success2, active_shift, msg2 = await self.db.start_shift(guild_id, user_id, user_name, start_time)
        self.assertFalse(success2)
        self.assertIn("Zaten", msg2)
        self.assertEqual(active_shift["id"], shift["id"])

    async def test_end_shift_duration_calculation(self):
        """Mesai bitirme ve süre hesaplama testi."""
        guild_id = 9999
        user_id = 54321
        user_name = "StaffMember"
        start_time = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
        # 2 saat 30 dakika 15 saniye sonrası
        end_time = start_time + timedelta(hours=2, minutes=30, seconds=15)

        # Mesai başlat
        await self.db.start_shift(guild_id, user_id, user_name, start_time)

        # Mesai bitir
        success, result, msg = await self.db.end_shift(guild_id, user_id, end_time)
        self.assertTrue(success)
        self.assertIsNotNone(result)
        expected_seconds = 2 * 3600 + 30 * 60 + 15
        self.assertEqual(result["duration_seconds"], expected_seconds)
        self.assertEqual(result["total_completed_shifts"], 1)
        self.assertEqual(result["total_lifetime_seconds"], expected_seconds)

        # Açık mesai yokken tekrar bitirmeyi dene
        success_empty, result_empty, msg_empty = await self.db.end_shift(guild_id, user_id, end_time)
        self.assertFalse(success_empty)
        self.assertIn("bulunmamaktadır", msg_empty)

    async def test_guild_reports_and_multiple_shifts(self):
        """Toplu raporlama ve çoklu mesai hesaplama testi."""
        guild_id = 8888
        u1, u2 = 101, 102
        t0 = datetime(2026, 8, 27, 9, 0, 0, tzinfo=timezone.utc)

        # U1: 1. vardiya (1 saat)
        await self.db.start_shift(guild_id, u1, "UserOne", t0)
        await self.db.end_shift(guild_id, u1, t0 + timedelta(hours=1))

        # U1: 2. vardiya (2 saat)
        await self.db.start_shift(guild_id, u1, "UserOne", t0 + timedelta(hours=2))
        await self.db.end_shift(guild_id, u1, t0 + timedelta(hours=4))

        # U2: 1. vardiya (45 dakika)
        await self.db.start_shift(guild_id, u2, "UserTwo", t0)
        await self.db.end_shift(guild_id, u2, t0 + timedelta(minutes=45))

        # Rapor al
        reports = await self.db.get_guild_report(guild_id)
        self.assertEqual(len(reports), 2)
        
        # U1 ilk sırada olmalı (toplam 3 saat = 10800 sn)
        self.assertEqual(reports[0]["user_id"], u1)
        self.assertEqual(reports[0]["shift_count"], 2)
        self.assertEqual(reports[0]["total_duration"], 3 * 3600)

        # U2 ikinci sırada olmalı (toplam 45 dk = 2700 sn)
        self.assertEqual(reports[1]["user_id"], u2)
        self.assertEqual(reports[1]["shift_count"], 1)
        self.assertEqual(reports[1]["total_duration"], 45 * 60)

    async def test_force_end_shift(self):
        """Yönetici tarafından mesai zorla kapatma testi."""
        guild_id = 7777
        user_id = 701
        start_time = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)

        await self.db.start_shift(guild_id, user_id, "ForgottenUser", start_time)
        active = await self.db.get_active_shift(guild_id, user_id)
        self.assertIsNotNone(active)

        success, result, msg = await self.db.force_end_shift(guild_id, user_id, "AdminUser")
        self.assertTrue(success)

        # Artık aktif mesaisi olmamalı
        active_after = await self.db.get_active_shift(guild_id, user_id)
        self.assertIsNone(active_after)

    def test_duration_formatter(self):
        """Formatlayıcı metin testi."""
        self.assertEqual(format_duration(0), "0 sn")
        self.assertEqual(format_duration(45), "45 sn")
        self.assertEqual(format_duration(125), "2 dk 5 sn")
        self.assertEqual(format_duration(3665), "1 saat 1 dk 5 sn")
        self.assertEqual(format_duration(7200), "2 saat")

if __name__ == "__main__":
    unittest.main()
