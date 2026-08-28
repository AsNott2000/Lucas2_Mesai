import io
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import discord
from database import db
from services.panel_manager import panel_manager
from services.notification_service import notification_service
from utils.permissions import has_admin_permission
from utils.formatters import (
    create_admin_report_embed,
    create_active_shifts_embed,
    create_error_embed,
    create_warning_embed,
    create_log_embed,
    create_report_and_reset_summary_embed,
    generate_shift_report_txt,
    format_duration,
    parse_iso_or_datetime,
)

logger = logging.getLogger("Lucas2MesaiBot.AdminView")

# ==============================================================================
# ONAY VE ETKİLEŞİM VİEW BİLEŞENLERİ (CONFIRMATION & SELECT VIEWS)
# ==============================================================================

class ReportResetConfirmView(discord.ui.View):
    """
    Genel Rapor Alma ve Dönem Sıfırlama işlemi için güvenlik onay view'i.
    Raporu .txt formatında derler, teslim eder ve ardından dönem verilerini sıfırlar.
    """

    def __init__(self, guild_id: int):
        super().__init__(timeout=60)
        self.guild_id = guild_id

    @discord.ui.button(
        label="Evet, Onayla",
        style=discord.ButtonStyle.danger,
        emoji="✅",
        custom_id="btn_confirm_report_reset"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild or guild.id != self.guild_id:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Sunucu doğrulanamadı."),
                ephemeral=True
            )
            return

        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi tamamlama yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            now = datetime.now(timezone.utc)
            admin_name = interaction.user.display_name

            # 1. Devam eden tüm aktif mesaileri anlık zaman damgasıyla otomatik kapat
            closed_active_count, closed_records = await db.force_end_all_shifts(
                guild_id=guild.id,
                admin_name=admin_name
            )

            # 2. Kapatılan ve geçmiş tüm mesai kayıtlarını derle
            reports = await db.get_guild_report(guild.id)
            detailed_shifts = await db.get_guild_detailed_shifts(guild.id)

            reported_user_count = len(reports)
            total_shifts_count = sum(r.get("shift_count", 0) for r in reports)
            total_duration_seconds = sum(r.get("total_duration", 0) for r in reports)

            # 3. .txt rapor metnini oluştur ve bellek üzerinde dosya akışına (io.BytesIO) dönüştür
            txt_content = generate_shift_report_txt(
                guild_name=guild.name,
                reports=reports,
                detailed_shifts=detailed_shifts,
                admin_name=admin_name,
                report_time=now
            )
            filename = f"mesai-raporu-{now.strftime('%Y-%m-%d')}.txt"
            file_data = io.BytesIO(txt_content.encode("utf-8"))
            discord_file = discord.File(fp=file_data, filename=filename)

            # 4. Rapor teslim edilmeden önce özet embed'i hazırla
            # 5. Veritabanındaki ilgili dönem mesai kayıtlarını sıfırla / temizle
            deleted_records_count = await db.reset_guild_shifts(guild.id)

            # 6. Kapatılan aktif personellere DM ve alternatif kanal bildirimi gönder
            if closed_records and interaction.client:
                asyncio.create_task(
                    notification_service.notify_closed_shifts_on_report(
                        bot=interaction.client,
                        guild=guild,
                        closed_records=closed_records,
                        admin_name=admin_name
                    )
                )

            # 7. #aktif-mesailer ve #mesai-tablo panellerini anında sıfırlanmış duruma göre güncelle
            await panel_manager.update_all_panels(guild)

            # 7. Denetim logunu ilet
            log_embed = create_log_embed(
                action_type="REPORT_AND_RESET",
                user=interaction.user,
                details={
                    "👮 İşlemi Yapan Yetkili": admin_name,
                    "👥 Raporlanan Personel": f"{reported_user_count} kişi",
                    "📈 Toplam Oturum": f"{total_shifts_count} adet",
                    "⏳ Toplam Süre": format_duration(total_duration_seconds),
                    "🧹 Silinen Kayıt": f"{deleted_records_count} satır",
                    "🛑 Kapatılan Aktif Mesai": f"{closed_active_count} personel",
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)

            # 8. Yöneticiye rapor dosyasını ve özet embed'i ilet
            summary_embed = create_report_and_reset_summary_embed(
                admin=interaction.user,
                closed_active_count=closed_active_count,
                reported_user_count=reported_user_count,
                total_shifts_count=total_shifts_count,
                total_duration_seconds=total_duration_seconds,
                deleted_records_count=deleted_records_count,
                filename=filename
            )

            # Orijinal onay mesajını güncelle
            await interaction.edit_original_response(
                content="✅ **Genel rapor başarıyla oluşturuldu ve veritabanı sıfırlandı.**",
                embed=summary_embed,
                view=None,
                attachments=[discord_file]
            )

        except Exception as e:
            logger.error(f"Rapor oluşturma ve veri sıfırlama sırasında hata ({guild.name}): {e}", exc_info=True)
            await interaction.followup.send(
                embed=create_error_embed("İşlem Hatası", f"Rapor oluşturulurken bir hata meydana geldi: `{e}`"),
                ephemeral=True
            )

    @discord.ui.button(
        label="İptal",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="btn_cancel_report_reset"
    )
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ **İşlem iptal edildi.** Veritabanında hiçbir değişiklik yapılmadı.",
            embed=None,
            view=None
        )


class ForceCloseAllConfirmView(discord.ui.View):
    """
    Tüm aktif mesaileri toplu kapatma işlemi için güvenlik onay view'i.
    """

    def __init__(self, guild_id: int):
        super().__init__(timeout=60)
        self.guild_id = guild_id

    @discord.ui.button(
        label="Onayla",
        style=discord.ButtonStyle.danger,
        emoji="🛑",
        custom_id="btn_confirm_close_all"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild or guild.id != self.guild_id:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Sunucu doğrulanamadı."),
                ephemeral=True
            )
            return

        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        now = datetime.now(timezone.utc)
        count, closed_records = await db.force_end_all_shifts(
            guild_id=guild.id,
            admin_name=interaction.user.display_name
        )

        # Mesaisi kapatılan personellere DM ve alternatif kanal bildirimi gönder
        if closed_records and interaction.client:
            asyncio.create_task(
                notification_service.notify_closed_shifts_on_report(
                    bot=interaction.client,
                    guild=guild,
                    closed_records=closed_records,
                    admin_name=interaction.user.display_name
                )
            )

        # Canlı Panelleri Anında Güncelle
        await panel_manager.update_all_panels(guild)

        # Denetim Logunu Gönder
        log_embed = create_log_embed(
            action_type="FORCE_CLOSED_ALL",
            user=interaction.user,
            details={
                "👮 İşlemi Yapan Yetkili": interaction.user.display_name,
                "👥 Kapatılan Mesai Sayısı": f"{count} personel",
                "🕒 Kapatılma Zamanı": f"<t:{int(now.timestamp())}:F>"
            }
        )
        await panel_manager.send_audit_log(guild, log_embed)

        # Yöneticiye Özet Ephemeral Rapor Hazırla
        summary_embed = discord.Embed(
            title="🛑 Tüm Aktif Mesailer Başarıyla Kapatıldı",
            description=f"Sunucudaki **{count}** personelin açık olan mesai oturumu başarıyla sonlandırıldı.",
            color=0xE74C3C
        )
        summary_embed.add_field(name="👮 Kapatan Yetkili", value=interaction.user.mention, inline=True)
        summary_embed.add_field(name="👥 Kapatılan Personel Sayısı", value=f"**{count}** kişi", inline=True)
        summary_embed.add_field(name="🕒 Kapatılma Zamanı", value=f"<t:{int(now.timestamp())}:F>", inline=False)

        if closed_records:
            user_list = [
                f"• <@{rec['user_id']}> (`{rec['user_name']}`) — Süre: `{format_duration(rec['duration_seconds'])}`"
                for rec in closed_records[:10]
            ]
            if len(closed_records) > 10:
                user_list.append(f"... ve {len(closed_records) - 10} kişi daha.")
            summary_embed.add_field(name="📋 Kapatılan Personeller", value="\n".join(user_list), inline=False)

        summary_embed.set_footer(text="Lucas2 Yönetim Paneli • Canlı Paneller Güncellendi")
        summary_embed.timestamp = now

        await interaction.edit_original_response(
            content=None,
            embed=summary_embed,
            view=None
        )

    @discord.ui.button(
        label="Vazgeç",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="btn_cancel_close_all"
    )
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ **Toplu mesai kapatma işlemi iptal edildi.**",
            embed=None,
            view=None
        )


class SingleUserCloseSelect(discord.ui.Select):
    """Yalnızca aktif mesaide olan personelleri listeleyen seçim menüsü."""

    def __init__(self, active_shifts: List[Dict[str, Any]]):
        options = []
        now = datetime.now(timezone.utc)

        for shift in active_shifts[:25]:  # Discord select menu sınırı: 25 seçenek
            user_id = shift["user_id"]
            user_name = shift.get("user_name", f"Kullanıcı-{user_id}")
            start_raw = shift.get("start_time")
            start_dt = parse_iso_or_datetime(start_raw)

            if start_dt:
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                elapsed_sec = max(0, int((now - start_dt).total_seconds()))
                elapsed_text = format_duration(elapsed_sec)
                clock_text = start_dt.strftime("%H:%M")
                desc = f"Başlangıç: {clock_text} | Süre: {elapsed_text}"[:100]
            else:
                desc = f"ID: {user_id}"

            options.append(
                discord.SelectOption(
                    label=user_name[:100],
                    value=str(user_id),
                    description=desc,
                    emoji="🟢"
                )
            )

        super().__init__(
            placeholder="Mesaisini kapatmak istediğiniz personeli seçiniz...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Sunucu doğrulanamadı."),
                ephemeral=True
            )
            return

        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        selected_user_id = int(self.values[0])
        admin_name = interaction.user.display_name

        await interaction.response.defer(ephemeral=True)

        success, result, message = await db.force_end_shift(
            guild_id=guild.id,
            user_id=selected_user_id,
            admin_name=admin_name
        )

        if not success or not result:
            await interaction.edit_original_response(
                content=None,
                embed=create_error_embed("İşlem Başarısız", message),
                view=None
            )
            return

        # Canlı panelleri güncelle
        await panel_manager.update_all_panels(guild)

        # Denetim logunu gönder
        target_member = guild.get_member(selected_user_id)
        log_embed = create_log_embed(
            action_type="FORCE_CLOSED",
            user=target_member,
            details={
                "👮 Kapatan Yetkili": admin_name,
                "👤 Kapatılan Personel ID": str(selected_user_id),
                "⌛ Oturum Süresi": format_duration(result["duration_seconds"])
            }
        )
        await panel_manager.send_audit_log(guild, log_embed)

        # Yöneticiye onay embed'i
        confirm_embed = discord.Embed(
            title="🛑 Personel Mesaisi Başarıyla Sonlandırıldı",
            description=f"<@{selected_user_id}> (`{result.get('id', '')}`) personelinin açık olan mesai oturumu başarıyla kapatıldı.",
            color=0xE67E22
        )
        confirm_embed.add_field(name="👮 Kapatan Yetkili", value=interaction.user.mention, inline=True)
        confirm_embed.add_field(name="⌛ Kaydedilen Süre", value=f"**{format_duration(result['duration_seconds'])}**", inline=True)
        confirm_embed.set_footer(text="Lucas2 Yönetim Paneli • Canlı Paneller Güncellendi")
        confirm_embed.timestamp = datetime.now(timezone.utc)

        await interaction.edit_original_response(
            content=None,
            embed=confirm_embed,
            view=None
        )


class SingleUserCloseSelectView(discord.ui.View):
    """Kişi bazlı mesai kapatma seçim menüsünü barındıran View."""

    def __init__(self, active_shifts: List[Dict[str, Any]]):
        super().__init__(timeout=60)
        self.add_item(SingleUserCloseSelect(active_shifts))

    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, emoji="❌", row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ **İşlem iptal edildi.**",
            embed=None,
            view=None
        )


# ==============================================================================
# MANUEL MESAİ DÜZENLEME (EKLE / SİL) VİEW VE MODAL BİLEŞENLERİ
# ==============================================================================

class ManualUserSelect(discord.ui.UserSelect):
    """Sunucudaki üyeler arasından personel seçimi yaptıran UserSelect menüsü."""

    def __init__(self):
        super().__init__(
            placeholder="Mesai süresi düzenlenecek personeli seçiniz...",
            min_values=1,
            max_values=1,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Sunucu doğrulanamadı."),
                ephemeral=True
            )
            return

        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        selected_user = self.values[0]  # discord.User | discord.Member
        user_stats = await db.get_user_stats(guild.id, selected_user.id)
        current_total = user_stats["total_duration"]

        embed = discord.Embed(
            title="⏱️ Manuel Mesai Düzenleme - İşlem Türü Seçimi",
            description=(
                f"👤 **Seçilen Personel:** {selected_user.mention} (`{selected_user.display_name}`)\n"
                f"📊 **Mevcut Toplam Mesai Süresi:** **{format_duration(current_total)}**\n\n"
                f"Lütfen uygulamak istediğiniz işlem türünü seçiniz:"
            ),
            color=0x3498DB
        )
        embed.set_footer(text="Lucas2 Yönetim Paneli • Adım 2/3")

        view = ManualActionTypeView(target_user=selected_user, current_total_seconds=current_total)
        await interaction.response.edit_message(
            embed=embed,
            view=view
        )


class ManualTimeAdjustUserSelectView(discord.ui.View):
    """Personel seçim arayüzünü (UserSelect) barındıran View."""

    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ManualUserSelect())

    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, emoji="❌", row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ **Manuel mesai düzenleme işlemi iptal edildi.**",
            embed=None,
            view=None
        )


class ManualActionTypeView(discord.ui.View):
    """İşlem tipini (Süre Ekle / Süre Sil) seçtiren View."""

    def __init__(self, target_user: discord.User | discord.Member, current_total_seconds: int):
        super().__init__(timeout=120)
        self.target_user = target_user
        self.current_total_seconds = current_total_seconds

    @discord.ui.button(
        label="Süre Ekle (+)",
        style=discord.ButtonStyle.success,
        emoji="➕",
        custom_id="btn_manual_add_time"
    )
    async def add_time_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        modal = ManualTimeAdjustModal(
            target_user=self.target_user,
            action_type="add",
            current_total_seconds=self.current_total_seconds
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Süre Sil (-)",
        style=discord.ButtonStyle.danger,
        emoji="➖",
        custom_id="btn_manual_deduct_time"
    )
    async def deduct_time_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        modal = ManualTimeAdjustModal(
            target_user=self.target_user,
            action_type="deduct",
            current_total_seconds=self.current_total_seconds
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="İptal",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="btn_cancel_action_type"
    )
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ **Manuel mesai düzenleme işlemi iptal edildi.**",
            embed=None,
            view=None
        )


class ManualTimeAdjustModal(discord.ui.Modal):
    """
    Düzenlenecek dakika ve açıklama girişini alan Modal penceresi.
    """

    def __init__(
        self,
        target_user: discord.User | discord.Member,
        action_type: str,
        current_total_seconds: int
    ):
        title = "Mesai Süresi Ekle (+)" if action_type == "add" else "Mesai Süresi Sil (-)"
        super().__init__(title=title[:45])
        self.target_user = target_user
        self.action_type = action_type
        self.current_total_seconds = current_total_seconds

        self.duration_input = discord.ui.TextInput(
            label="Düzenlenecek Süre (Dakika)",
            placeholder="Örn: 30 (Yalnızca pozitif tam sayı)",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.duration_input)

        self.reason_input = discord.ui.TextInput(
            label="Düzenleme Nedeni / Açıklama (Opsiyonel)",
            placeholder="Örn: Telafi mesaisi / Manuel düzeltme",
            style=discord.TextStyle.paragraph,
            max_length=200,
            required=False
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Doğrulama: Süre pozitif tam sayı olmalı
        duration_val_str = self.duration_input.value.strip()
        if not duration_val_str.isdigit() or int(duration_val_str) <= 0:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Geçersiz Süre Girişi",
                    "Lütfen 0'dan büyük, pozitif bir tam sayı giriniz (Örn: 15, 30, 60)."
                ),
                ephemeral=True
            )
            return

        minutes = int(duration_val_str)
        reason = self.reason_input.value.strip() or "Belirtilmedi"
        adjustment_seconds = minutes * 60

        # Yeni toplam süreyi hesapla
        if self.action_type == "add":
            action_text = "EKLENECEK"
            action_symbol = "+"
            new_total = self.current_total_seconds + adjustment_seconds
        else:
            action_text = "SİLİNECEK"
            action_symbol = "-"
            new_total = max(0, self.current_total_seconds - adjustment_seconds)

        # 2. Güvenlik Onayı Mesajı (Confirmation Flow)
        confirm_embed = discord.Embed(
            title="⚠️ Manuel Mesai Düzenleme Güvenlik Onayı",
            description=(
                f"**{self.target_user.display_name}** (`{self.target_user.id}`) adlı personelin mesai süresine "
                f"**{minutes} dakika** **{action_text}**.\n\n"
                f"**İşlem Detayları:**\n"
                f"• **İşlem Türü:** `{action_symbol}{minutes} Dakika` ({'Süre Ekleme' if self.action_type == 'add' else 'Süre Silme'})\n"
                f"• **Mevcut Toplam Süre:** `{format_duration(self.current_total_seconds)}`\n"
                f"• **İşlem Sonrası Toplam Süre:** `{format_duration(new_total)}`\n"
                f"• **Gerekçe / Açıklama:** {reason}\n\n"
                f"Bu işlemi onaylıyor musunuz?"
            ),
            color=0xE67E22 if self.action_type == "add" else 0xE74C3C
        )
        confirm_embed.set_footer(text="Lucas2 Güvenlik Doğrulaması • Lütfen teyit ediniz.")

        guild_id = interaction.guild_id or (interaction.guild.id if interaction.guild else 0)
        view = ManualTimeAdjustConfirmView(
            guild_id=guild_id,
            target_user=self.target_user,
            action_type=self.action_type,
            minutes=minutes,
            reason=reason,
            current_total_seconds=self.current_total_seconds,
            new_total_seconds=new_total
        )

        await interaction.response.send_message(
            embed=confirm_embed,
            view=view,
            ephemeral=True
        )


class ManualTimeAdjustConfirmView(discord.ui.View):
    """Nihai Onayla / İptal onay View'i."""

    def __init__(
        self,
        guild_id: int,
        target_user: discord.User | discord.Member,
        action_type: str,
        minutes: int,
        reason: str,
        current_total_seconds: int,
        new_total_seconds: int
    ):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.target_user = target_user
        self.action_type = action_type
        self.minutes = minutes
        self.reason = reason
        self.current_total_seconds = current_total_seconds
        self.new_total_seconds = new_total_seconds

    @discord.ui.button(
        label="Onayla",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="btn_confirm_manual_adjust"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild or guild.id != self.guild_id:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Sunucu doğrulanamadı."),
                ephemeral=True
            )
            return

        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır."),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            admin_name = interaction.user.display_name

            # Veritabanında süreyi güncelle ve kayıt ekle
            success, result_data, msg = await db.adjust_user_shift_duration(
                guild_id=guild.id,
                user_id=self.target_user.id,
                user_name=self.target_user.display_name,
                adjustment_minutes=self.minutes,
                action_type=self.action_type,
                admin_name=admin_name,
                reason=self.reason
            )

            if not success:
                await interaction.edit_original_response(
                    content=None,
                    embed=create_error_embed("İşlem Başarısız", msg),
                    view=None
                )
                return

            actual_new_total = result_data["new_total_seconds"]

            # #mesai-tablo canlı panelini anında güncelle
            await panel_manager.update_leaderboard_panel(guild)

            # Denetim Logunu Gönder (#mesai-log)
            action_symbol = "+" if self.action_type == "add" else "-"
            log_embed = create_log_embed(
                action_type="MANUAL_ADJUST",
                user=self.target_user,
                details={
                    "👮 Düzenleyen Yetkili": admin_name,
                    "⚙️ İşlem": f"{action_symbol}{self.minutes} Dakika ({'Süre Ekleme' if self.action_type == 'add' else 'Süre Silme'})",
                    "⌛ Eski Toplam Süre": format_duration(result_data["old_total_seconds"]),
                    "⏱️ Yeni Toplam Süre": format_duration(actual_new_total),
                    "📝 Gerekçe": self.reason
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)

            # Yöneticiye Bilgilendirme Embedi
            success_embed = discord.Embed(
                title="✅ Manuel Mesai Düzenlemesi Başarılı",
                description=(
                    f"**{self.target_user.mention}** (`{self.target_user.display_name}`) adlı personelin mesai süresi "
                    f"başarıyla güncellendi."
                ),
                color=0x2ECC71
            )
            success_embed.add_field(name="👮 Yetkili", value=interaction.user.mention, inline=True)
            success_embed.add_field(name="⚙️ Uygulanan Değişiklik", value=f"**{action_symbol}{self.minutes} dk**", inline=True)
            success_embed.add_field(name="⏱️ Yeni Toplam Süre", value=f"**{format_duration(actual_new_total)}**", inline=True)
            success_embed.add_field(name="📝 Açıklama", value=self.reason, inline=False)
            success_embed.set_footer(text="Lucas2 Yönetim Paneli • #mesai-tablo Güncellendi")
            success_embed.timestamp = datetime.now(timezone.utc)

            await interaction.edit_original_response(
                content=None,
                embed=success_embed,
                view=None
            )

        except Exception as e:
            logger.error(f"Manuel mesai düzenleme sırasında hata ({guild.name}): {e}", exc_info=True)
            await interaction.edit_original_response(
                content=None,
                embed=create_error_embed("İşlem Hatası", f"İşlem sırasında beklenmedik bir hata oluştu: `{e}`"),
                view=None
            )

    @discord.ui.button(
        label="İptal",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="btn_cancel_manual_adjust"
    )
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ **Manuel mesai düzenleme işlemi iptal edildi.** Herhangi bir değişiklik yapılmadı.",
            embed=None,
            view=None
        )


# ==============================================================================
# ANA YÖNETİM PANELİ (PERSISTENT ADMIN VIEW)
# ==============================================================================

class AdminView(discord.ui.View):
    """
    #admin-settings kanalındaki kalıcı (Persistent) yönetim butonlarını barındıran View sınıfı.
    timeout=None ve custom_id değerleri sayesinde bot restart attığında da yetki doğrulamasıyla çalışır.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Genel Rapor Al",
        style=discord.ButtonStyle.primary,
        emoji="📊",
        custom_id="btn_get_report",
        row=0
    )
    async def get_report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Rapor alma ve dönem sıfırlama akışını başlatır.
        Doğrudan işlem yapmaz, ephemeral onay dialogu açar.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır. Yalnızca Yöneticiler veya Yetkili Rolüne sahip kişiler erişebilir."
                ),
                ephemeral=True
            )
            return

        # Ephemeral Onay Adımı (Confirmation Dialog)
        confirm_embed = discord.Embed(
            title="⚠️ Genel Rapor Alma & Veri Sıfırlama Onayı",
            description=(
                "**Emin misiniz?**\n\n"
                "• Devam eden tüm aktif mesailer anlık olarak kapatılacaktır.\n"
                "• Tüm mesai verileri derlenerek biçimlendirilmiş bir `.txt` raporu olarak iletilecektir.\n"
                "• Rapor teslim edildikten sonra mevcut tüm mesai verileri **kalıcı olarak silinecektir / sıfırlanacaktır**.\n"
                "• Canlı paneller sıfırlanacaktır."
            ),
            color=0xE67E22
        )
        confirm_embed.set_footer(text="Lucas2 Güvenlik Doğrulaması • Lütfen işleminizi teyit ediniz.")

        view = ReportResetConfirmView(guild_id=guild.id)
        await interaction.response.send_message(
            embed=confirm_embed,
            view=view,
            ephemeral=True
        )

    @discord.ui.button(
        label="Anlık Aktif Mesailer",
        style=discord.ButtonStyle.secondary,
        emoji="🟢",
        custom_id="btn_active_shifts",
        row=0
    )
    async def active_shifts_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Şu anda aktif görevde olan personelleri anlık listeler."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu bilgiyi görüntüleme yetkiniz bulunmamaktadır."
                ),
                ephemeral=True
            )
            return

        active_shifts = await db.get_all_active_shifts(guild.id)
        embed = create_active_shifts_embed(active_shifts)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Tüm Mesaileri Kapat",
        style=discord.ButtonStyle.danger,
        emoji="🛑",
        custom_id="btn_force_close_all",
        row=1
    )
    async def force_close_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Sunucuda devam eden tüm aktif mesaileri sonlandırmak için güvenlik onay diyaloğu açar.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır. Yalnızca Yöneticiler veya Yetkili Rolüne sahip kişiler erişebilir."
                ),
                ephemeral=True
            )
            return

        # Aktif mesaileri sorgula
        active_shifts = await db.get_all_active_shifts(guild.id)
        if not active_shifts:
            await interaction.response.send_message(
                embed=create_warning_embed(
                    title="Aktif Mesai Bulunamadı",
                    message="Şu anda sunucuda devam eden aktif bir personel mesaisi bulunmamaktadır."
                ),
                ephemeral=True
            )
            return

        # Ephemeral Güvenlik Onayı
        confirm_embed = discord.Embed(
            title="⚠️ Toplu Mesai Kapatma Güvenlik Onayı",
            description=(
                f"Şu anda görevde olan **{len(active_shifts)}** personelin mesaisi sonlandırılacaktır.\n\n"
                "**Tüm aktif çalışanların mesaisini sonlandırmak istediğinize emin misiniz?**"
            ),
            color=0xE74C3C
        )
        confirm_embed.set_footer(text="Lucas2 Güvenlik Doğrulaması")

        view = ForceCloseAllConfirmView(guild_id=guild.id)
        await interaction.response.send_message(
            embed=confirm_embed,
            view=view,
            ephemeral=True
        )

    @discord.ui.button(
        label="Kişi Mesaisi Kapat",
        style=discord.ButtonStyle.secondary,
        emoji="👤",
        custom_id="btn_close_single_user",
        row=1
    )
    async def close_single_user_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Yalnızca o an aktif mesaide olan personelleri listeleyen bir seçim menüsü açar.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır. Yalnızca Yöneticiler veya Yetkili Rolüne sahip kişiler erişebilir."
                ),
                ephemeral=True
            )
            return

        # Aktif mesaileri sorgula
        active_shifts = await db.get_all_active_shifts(guild.id)
        if not active_shifts:
            await interaction.response.send_message(
                embed=create_warning_embed(
                    title="Aktif Mesai Bulunamadı",
                    message="Şu anda sunucuda devam eden aktif bir personel mesaisi bulunmamaktadır."
                ),
                ephemeral=True
            )
            return

        prompt_embed = discord.Embed(
            title="👤 Kişi Bazlı Mesai Sonlandırma",
            description="Aşağıdaki menüden mesaisini kapatmak istediğiniz aktif personeli seçiniz:",
            color=0x3498DB
        )
        view = SingleUserCloseSelectView(active_shifts)
        await interaction.response.send_message(
            embed=prompt_embed,
            view=view,
            ephemeral=True
        )

    @discord.ui.button(
        label="Manuel Mesai Düzenle",
        style=discord.ButtonStyle.primary,
        emoji="⏱️",
        custom_id="btn_manual_time_adjust",
        row=2
    )
    async def manual_time_adjust_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Personel mesai süresine manuel dakika ekleme veya silme akışını başlatır."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır. Yalnızca Yöneticiler veya Yetkili Rolüne sahip kişiler erişebilir."
                ),
                ephemeral=True
            )
            return

        prompt_embed = discord.Embed(
            title="⏱️ Manuel Mesai Süresi Düzenleme",
            description=(
                "Mesai süresine manuel ekleme yapmak veya süresinden düşmek istediğiniz personeli "
                "aşağıdaki menüden seçiniz."
            ),
            color=0x3498DB
        )
        view = ManualTimeAdjustUserSelectView()
        await interaction.response.send_message(
            embed=prompt_embed,
            view=view,
            ephemeral=True
        )
