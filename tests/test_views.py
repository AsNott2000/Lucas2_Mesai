import unittest
import discord
from views.shift_view import ShiftView
from views.admin_view import (
    AdminView,
    ReportResetConfirmView,
    ForceCloseAllConfirmView,
    SingleUserCloseSelectView,
    ManualUserSelect,
    ManualTimeAdjustUserSelectView,
    ManualActionTypeView,
    ManualTimeAdjustModal,
    ManualTimeAdjustConfirmView,
)
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
    create_report_and_reset_summary_embed,
    create_warning_embed,
    create_error_embed,
    create_log_embed,
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
        self.assertIn("btn_force_close_all", custom_ids)
        self.assertIn("btn_close_single_user", custom_ids)
        self.assertIn("btn_manual_time_adjust", custom_ids)

    def test_manual_time_adjust_user_select_view(self):
        """ManualTimeAdjustUserSelectView menü ve buton yapısını test et."""
        view = ManualTimeAdjustUserSelectView()
        self.assertEqual(view.timeout, 120)

        user_selects = [item for item in view.children if isinstance(item, discord.ui.UserSelect)]
        self.assertEqual(len(user_selects), 1)

        buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0].label, "İptal")

    def test_manual_action_type_view(self):
        """ManualActionTypeView butonlarını test et."""
        from unittest.mock import MagicMock
        mock_user = MagicMock(spec=discord.User)
        mock_user.id = 123
        mock_user.display_name = "TestPersonel"

        view = ManualActionTypeView(target_user=mock_user, current_total_seconds=3600)
        self.assertEqual(view.timeout, 120)

        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_manual_add_time", custom_ids)
        self.assertIn("btn_manual_deduct_time", custom_ids)
        self.assertIn("btn_cancel_action_type", custom_ids)

    def test_manual_time_adjust_modal(self):
        """ManualTimeAdjustModal alanlarını ve başlığını test et."""
        from unittest.mock import MagicMock
        mock_user = MagicMock(spec=discord.User)
        mock_user.id = 123
        mock_user.display_name = "TestPersonel"

        modal_add = ManualTimeAdjustModal(target_user=mock_user, action_type="add", current_total_seconds=3600)
        self.assertIn("Ekle", modal_add.title)
        self.assertEqual(len(modal_add.children), 2)
        self.assertTrue(modal_add.duration_input.required)
        self.assertFalse(modal_add.reason_input.required)

        modal_deduct = ManualTimeAdjustModal(target_user=mock_user, action_type="deduct", current_total_seconds=3600)
        self.assertIn("Sil", modal_deduct.title)

    def test_manual_time_adjust_confirm_view(self):
        """ManualTimeAdjustConfirmView butonlarını test et."""
        from unittest.mock import MagicMock
        mock_user = MagicMock(spec=discord.User)
        mock_user.id = 123

        view = ManualTimeAdjustConfirmView(
            guild_id=111,
            target_user=mock_user,
            action_type="add",
            minutes=30,
            reason="Test",
            current_total_seconds=1000,
            new_total_seconds=2800
        )
        self.assertEqual(view.timeout, 60)
        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_confirm_manual_adjust", custom_ids)
        self.assertIn("btn_cancel_manual_adjust", custom_ids)

    def test_report_reset_confirm_view_properties(self):
        """ReportResetConfirmView butonlarını ve timeout değerini test et."""
        view = ReportResetConfirmView(guild_id=12345)
        self.assertEqual(view.timeout, 60)
        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_confirm_report_reset", custom_ids)
        self.assertIn("btn_cancel_report_reset", custom_ids)

    def test_force_close_all_confirm_view_properties(self):
        """ForceCloseAllConfirmView butonlarını ve timeout değerini test et."""
        view = ForceCloseAllConfirmView(guild_id=12345)
        self.assertEqual(view.timeout, 60)
        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_confirm_close_all", custom_ids)
        self.assertIn("btn_cancel_close_all", custom_ids)

    def test_single_user_close_select_view(self):
        """SingleUserCloseSelectView seçeneklerini ve menü yapısını test et."""
        mock_active = [
            {"user_id": 101, "user_name": "Personel1", "start_time": "2026-08-27T08:00:00+00:00"},
            {"user_id": 102, "user_name": "Personel2", "start_time": "2026-08-27T09:00:00+00:00"}
        ]
        view = SingleUserCloseSelectView(mock_active)
        self.assertEqual(view.timeout, 60)
        
        selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
        self.assertEqual(len(selects), 1)
        options = selects[0].options
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].value, "101")
        self.assertEqual(options[0].label, "Personel1")
        self.assertEqual(options[1].value, "102")
        self.assertEqual(options[1].label, "Personel2")

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
        self.assertIn("Tüm Mesaileri Kapat", admin_embed.description)
        self.assertIn("Kişi Mesaisi Kapat", admin_embed.description)

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

        # Mock User
        class MockUser:
            display_name = "Mehmet"
            name = "mehmet"
            mention = "<@222>"
            id = 222

        # Reset summary embed testi
        summary_embed = create_report_and_reset_summary_embed(
            admin=MockUser(),
            closed_active_count=2,
            reported_user_count=5,
            total_shifts_count=10,
            total_duration_seconds=36000,
            deleted_records_count=10,
            filename="mesai-raporu-2026-08-28.txt"
        )
        self.assertIn("Dönem Raporu", summary_embed.title)
        self.assertIn("mesai-raporu-2026-08-28.txt", summary_embed.fields[1].value)

        # AFK embed testleri
        afk_prompt = create_afk_prompt_embed(MockUser(), minutes_active=45, timeout_minutes=15, penalty_minutes=61)
        self.assertIn("DOĞRULAMASI", afk_prompt.title)
        self.assertIn("15 dakika", afk_prompt.description)
        self.assertIn("son 61 dakikalık süre silinir", afk_prompt.description)

        afk_ver = create_afk_verified_embed(MockUser())
        self.assertIn("Doğrulandı", afk_ver.title)

        afk_to = create_afk_timeout_embed(
            MockUser(),
            duration_seconds=3540,
            raw_duration_seconds=7200,
            deducted_seconds=3660,
            timeout_minutes=15,
            penalty_minutes=61
        )
        self.assertIn("Kapatıldı", afk_to.title)
        self.assertIn("Ham Oturum Süresi", afk_to.description)
        self.assertIn("Uygulanan Ceza", afk_to.description)
        self.assertIn("Son 61 dk silindi", afk_to.description)

if __name__ == "__main__":
    unittest.main()


