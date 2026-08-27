import unittest
import discord
from views.shift_view import ShiftView
from views.admin_view import AdminView
from views.afk_view import AFKVerificationView
from utils.formatters import (
    create_shift_panel_embed,
    create_admin_panel_embed,
    create_admin_report_embed,
    create_active_shifts_embed,
    create_live_active_shifts_embed,
    create_leaderboard_embed,
    create_afk_prompt_embed,
    create_afk_verified_embed,
    create_afk_timeout_embed,
    create_warning_embed,
    create_error_embed,
)

class TestViewsAndEmbeds(unittest.TestCase):
    """View bileşenleri ve embed doğrulama testleri."""

    def test_shift_view_properties(self):
        """ShiftView'in timeout ve custom_id'lerini doğrula."""
        view = ShiftView()
        self.assertIsNone(view.timeout, "ShiftView kalıcı olması için timeout=None olmalıdır.")

        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_start_shift", custom_ids)
        self.assertIn("btn_end_shift", custom_ids)

    def test_admin_view_properties(self):
        """AdminView'in timeout ve custom_id'lerini doğrula."""
        view = AdminView()
        self.assertIsNone(view.timeout, "AdminView kalıcı olması için timeout=None olmalıdır.")

        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_get_report", custom_ids)
        self.assertIn("btn_active_shifts", custom_ids)

    def test_afk_view_properties(self):
        """AFKVerificationView'in timeout ve custom_id'lerini doğrula."""
        view = AFKVerificationView()
        self.assertIsNone(view.timeout, "AFKVerificationView kalıcı olması için timeout=None olmalıdır.")

        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_afk_verify", custom_ids)

    def test_embed_creation(self):
        """Embed oluşturucuların hatasız çalıştığını doğrula."""
        panel_embed = create_shift_panel_embed()
        self.assertIn("MESAİ", panel_embed.title)

        admin_embed = create_admin_panel_embed()
        self.assertIn("YÖNETİCİ", admin_embed.title)

        warn_embed = create_warning_embed("Test Uyarı", "Açıklama")
        self.assertIn("⚠️", warn_embed.title)

        err_embed = create_error_embed("Test Hata", "Hata detayı")
        self.assertIn("❌", err_embed.title)

        # Canlı aktif mesailer embed testi
        mock_active = [
            {"user_id": 111, "user_name": "Ahmet", "start_time": "2026-08-27T08:00:00+00:00"}
        ]
        live_embed = create_live_active_shifts_embed(mock_active)
        self.assertIn("CANLI AKTİF", live_embed.title)

        # Liderlik tablosu embed testi
        mock_report = [
            {"user_id": 111, "user_name": "Ahmet", "shift_count": 5, "total_duration": 36000, "last_active": "2026-08-27T10:00:00+00:00"}
        ]
        rep_embed = create_leaderboard_embed(mock_report)
        self.assertIn("TABLOSU", rep_embed.title)

        # AFK embed testleri
        class MockUser:
            display_name = "Mehmet"
            name = "mehmet"
            mention = "<@222>"
            id = 222

        afk_prompt = create_afk_prompt_embed(MockUser())
        self.assertIn("DOĞRULAMASI", afk_prompt.title)

        afk_ver = create_afk_verified_embed(MockUser())
        self.assertIn("Doğrulandı", afk_ver.title)

        afk_to = create_afk_timeout_embed(MockUser(), 3600)
        self.assertIn("Kapatıldı", afk_to.title)

if __name__ == "__main__":
    unittest.main()

