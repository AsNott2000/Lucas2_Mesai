import unittest
from datetime import datetime, timedelta, timezone
from utils.formatters import (
    create_live_active_shifts_embed,
    create_leaderboard_embed,
    create_afk_prompt_embed,
    create_afk_timeout_embed,
    create_log_embed,
    format_duration,
)

class TestTrackerAndPanels(unittest.TestCase):
    """Canlı paneller ve AFK takip mekanizmaları doğrulama testleri."""

    def test_live_active_shifts_embed_empty(self):
        """Aktif mesai olmadığında doğru mesajın gösterildiğini doğrula."""
        embed = create_live_active_shifts_embed([])
        self.assertIn("kimse bulunmamaktadır", embed.description)
        self.assertEqual(len(embed.fields), 0)

    def test_live_active_shifts_embed_with_users(self):
        """Aktif mesaide personel varken embed alanlarının doğru oluştuğunu doğrula."""
        active_shifts = [
            {
                "user_id": 1001,
                "user_name": "Caner",
                "start_time": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            },
            {
                "user_id": 1002,
                "user_name": "Ece",
                "start_time": (datetime.now(timezone.utc) - timedelta(hours=1, minutes=15)).isoformat()
            }
        ]
        embed = create_live_active_shifts_embed(active_shifts)
        self.assertIn("2", embed.description)
        self.assertEqual(len(embed.fields), 2)
        self.assertIn("Caner", embed.fields[0].name)
        self.assertIn("Ece", embed.fields[1].name)

    def test_leaderboard_embed(self):
        """Sıralama tablosu madalya ve istatistik testi."""
        reports = [
            {"user_id": 1, "user_name": "Birinci", "shift_count": 10, "total_duration": 72000, "last_active": "2026-08-27T10:00:00+00:00"},
            {"user_id": 2, "user_name": "İkinci", "shift_count": 5, "total_duration": 36000, "last_active": "2026-08-27T09:00:00+00:00"},
            {"user_id": 3, "user_name": "Üçüncü", "shift_count": 2, "total_duration": 7200, "last_active": "2026-08-26T18:00:00+00:00"},
        ]
        embed = create_leaderboard_embed(reports)
        self.assertIn("TABLOSU", embed.title)
        # 1. alan sıralama tablosu, 2. alan genel istatistikler
        self.assertGreaterEqual(len(embed.fields), 2)
        ranking_field = embed.fields[0].value
        self.assertIn("🥇", ranking_field)
        self.assertIn("🥈", ranking_field)
        self.assertIn("🥉", ranking_field)

    def test_log_embeds(self):
        """Denetim log embedlerinin doğrulanması."""
        class MockUser:
            id = 555
            mention = "<@555>"
            display_name = "SuperAdmin"

        log = create_log_embed(
            action_type="AFK_TIMEOUT",
            user=MockUser(),
            details={"Süre": "45 dk", "Sebep": "Doğrulama zaman aşımı"}
        )
        self.assertIn("AFK", log.title)
        self.assertEqual(len(log.fields), 3)

        # Toplu kapatma log testi
        log_all = create_log_embed(
            action_type="FORCE_CLOSED_ALL",
            user=MockUser(),
            details={"Kapatılan Sayısı": "5 kişi"}
        )
        self.assertIn("Tüm Mesailer", log_all.title)
        self.assertEqual(len(log_all.fields), 2)

if __name__ == "__main__":
    unittest.main()
