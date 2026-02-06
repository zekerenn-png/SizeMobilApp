import flet as ft
from datetime import datetime
from supabase import create_client, Client
import warnings
import calendar

# --- 1. AYARLAR ---
warnings.filterwarnings("ignore") 

SUPABASE_URL = "https://tpegufrmxqkegetwdtwc.supabase.co"
SUPABASE_KEY = "sb_publishable_QB3jUBhZLVLFPe2FFLh_cA_B23_oVJj"

# Renkler
BG_COLOR = "#121212"
CARD_BG = "#1E1E1E"
TEXT_MAIN = "#FFFFFF"
TEXT_SEC = "#AAAAAA"
ACCENT = "#00E676"   # Yeşil (Gelir/Ciro)
ACCENT_SEC = "#2979FF" # Mavi (Stok/Net)
WARNING = "#FFAB00"  # Turuncu
DANGER = "#FF5252"   # Kırmızı (Gider)

# Supabase Bağlantısı
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print("Bağlantı Hatası:", e)

# --- 2. YARDIMCI FONKSİYONLAR ---
def tr_fix(text):
    if not text: return ""
    return str(text).replace('ğ','g').replace('ş','s').replace('ı','i').replace('ö','o').replace('ü','u').replace('ç','c')

def update_balance(table, id, amount):
    try:
        res = supabase.table(table).select("bakiye").eq("id", id).execute()
        if res.data:
            current = res.data[0]['bakiye'] or 0
            supabase.table(table).update({"bakiye": current + amount}).eq("id", id).execute()
    except: pass

def update_stok_adet(row_id, amount):
    try:
        res = supabase.table("stok").select("adet").eq("id", row_id).execute()
        if res.data:
            current = res.data[0]['adet'] or 0
            supabase.table("stok").update({"adet": current + amount}).eq("id", row_id).execute()
    except: pass

# --- 3. ANA UYGULAMA ---
def main(page: ft.Page):
    page.title = "SIZE MOBİL V7"
    page.theme_mode = "dark"
    page.bgcolor = BG_COLOR
    page.padding = 0
    page.scroll = "auto"
    page.window_width = 400
    page.window_height = 800

    def show_snack(txt, color=ACCENT):
        page.snack_bar = ft.SnackBar(content=ft.Text(txt, color="black", weight="bold"), bgcolor=color)
        page.snack_bar.open = True; page.update()

    class State:
        view = "AnaMenu" 
        view_cache = "Sevkiyatlar"
        kasa_modu = "Tahsilat"
        items_list = []
        rep_month = str(datetime.now().month)
        rep_year = str(datetime.now().year)
        detail_type = "Genel" # Ciro, Gider, KasaDetay

    def init_app_interface(user_role):
        page.clean()
        
        main_area = ft.Column(expand=True, scroll="auto", spacing=10)
        
        # Değişkenler
        rows_cont = ft.Column()
        cdrop = ft.Dropdown(label="Cari Seç", expand=True, bgcolor=BG_COLOR, border_radius=10)
        fmdrop = ft.Dropdown(label="Stoktan Model", expand=True, bgcolor=BG_COLOR, border_radius=10, disabled=True)
        fmtxt = ft.TextField(label="Hizmet/Ürün", expand=True, bgcolor=BG_COLOR, border_radius=10)
        firs = ft.TextField(label="İrsaliye", expand=True, bgcolor=BG_COLOR, border_radius=10)
        ffat = ft.TextField(label="Fatura", expand=True, bgcolor=BG_COLOR, border_radius=10)
        totallbl = ft.Text("₺0.00", size=24, weight="bold", color=ACCENT)
        tevdrop = ft.Dropdown(label="Tevkifat", options=[ft.dropdown.Option(x) for x in ["Yok","5/10","7/10","9/10","Tam"]], value="Yok", bgcolor=BG_COLOR, border_radius=10)

        # --- YARDIMCI FONKSİYONLAR ---
        def go_to(v):
            State.view = v
            render()

        def calc_total(e=None):
            t = 0
            tr = (1.0 if tevdrop.value=="Tam" else float(tevdrop.value.split('/')[0])/10.0) if tevdrop.value!="Yok" and tevdrop.visible else 0
            for row in State.items_list:
                try: 
                    t += (int(row['adet'].value) * float(row['fiyat'].value)) * (1 + int(row['kdv'].value)/100.0 * (1-tr))
                except: continue
            totallbl.value = f"₺{t:,.2f}"
            page.update()
            return t

        def add_item_row(e):
            r_adet = ft.TextField(label="Adet", width=80, value="1", bgcolor=BG_COLOR, on_change=calc_total)
            r_fiyat = ft.TextField(label="Fiyat", width=100, value="0", bgcolor=BG_COLOR, on_change=calc_total)
            r_kdv = ft.Dropdown(label="KDV", width=80, options=[ft.dropdown.Option("0"), ft.dropdown.Option("20")], value="20", bgcolor=BG_COLOR, on_change=calc_total)
            
            def delete_this_row(x):
                try:
                    State.items_list.remove(item_dict)
                    rows_cont.controls.remove(item_ui)
                    calc_total()
                except: pass

            item_ui = ft.Container(bgcolor=BG_COLOR, padding=10, border_radius=10, content=ft.Row([r_adet, r_fiyat, r_kdv, ft.IconButton(ft.Icons.DELETE, icon_color=DANGER, on_click=delete_this_row)]))
            item_dict = {"ui": item_ui, "adet": r_adet, "fiyat": r_fiyat, "kdv": r_kdv}
            State.items_list.append(item_dict)
            rows_cont.controls.append(item_ui)
            page.update()

        def save_full_form(e):
            if not cdrop.value or not firs.value: show_snack("Eksik Bilgi!", DANGER); return
            try:
                total = calc_total()
                tbl = "musteriler" if State.view_cache == "Sevkiyatlar" else "tedarikciler"
                cname = [x.text for x in cdrop.options if x.key==cdrop.value][0]
                model = fmdrop.value if State.view_cache=="Sevkiyatlar" else fmtxt.value
                
                supabase.table("islemler").insert({
                    "cari_id": int(cdrop.value), "cari_isim": cname, "cari_tip": tbl,
                    "irsaliye_no": firs.value, "fatura_no": ffat.value,
                    "tarih": datetime.now().strftime("%d.%m.%Y"),
                    "model_adi": model, "toplam_tutar": total, 
                    "islem_turu": "Satis" if State.view_cache=="Sevkiyatlar" else "Gider"
                }).execute()
                
                update_balance(tbl, int(cdrop.value), total if State.view_cache=="Sevkiyatlar" else -total)
                
                if State.view_cache=="Sevkiyatlar" and fmdrop.value:
                     sres = supabase.table("stok").select("id").eq("model_adi", fmdrop.value).limit(1).execute()
                     if sres.data: update_stok_adet(sres.data[0]['id'], -sum(int(x['adet'].value) for x in State.items_list))

                show_snack("İşlem Başarılı"); State.view = State.view_cache; render()
            except Exception as ex: show_snack(f"Hata: {ex}", DANGER)

        def delete_item(r):
            if r['islem_turu'] == "Satis": update_balance("musteriler", r['cari_id'], -r['toplam_tutar'])
            supabase.table("islemler").delete().eq("id", r['id']).execute(); render()

        def delete_cari(id, tbl):
            supabase.table(tbl).delete().eq("id", id).execute(); render()

        def create_card(content, on_click=None): 
            return ft.Container(
                content=content, bgcolor=CARD_BG, padding=15, border_radius=12, 
                margin=ft.margin.only(bottom=10), on_click=on_click, ink=True
            )
        
        def mobile_list_item(title, subtitle, right_top, right_bottom, color=ACCENT, on_delete=None):
            return create_card(ft.Row([
                ft.Column([
                    ft.Text(title, size=15, weight="bold", color=TEXT_MAIN),
                    ft.Text(subtitle, size=12, color=TEXT_SEC),
                ], expand=True),
                ft.Column([
                    ft.Text(right_top, size=14, weight="bold", color=color, text_align="right"),
                    ft.IconButton(ft.Icons.DELETE, icon_color=DANGER, icon_size=18, on_click=on_delete) if on_delete else ft.Container()
                ], alignment="end")
            ], alignment="spaceBetween"))

        # --- ANA RENDER ---
        def render():
            main_area.controls.clear()
            page.floating_action_button = None 
            
            # >>>> ANA MENÜ (DASHBOARD) <<<<
            if State.view == "AnaMenu":
                search = f".{State.rep_month.zfill(2)}.{State.rep_year}"
                rows = supabase.table("islemler").select("*").execute().data
                filtered = [r for r in rows if search in (r['tarih'] or "")]
                
                # Hesaplamalar
                ciro = sum(r['toplam_tutar'] for r in filtered if r['islem_turu'] == "Satis")
                gider = sum(r['toplam_tutar'] for r in filtered if r['islem_turu'] == "Gider")
                # Net Kasa = Tahsilat - Ödeme (Gerçek Para Akışı)
                tahsilat = sum(r['toplam_tutar'] for r in filtered if r['islem_turu'] == "Tahsilat")
                odeme = sum(r['toplam_tutar'] for r in filtered if r['islem_turu'] == "Odeme")
                net_kasa = tahsilat - odeme

                # Üst Kısım
                main_area.controls.append(ft.Row([ft.Text("SIZE TEKSTİL", size=22, weight="bold")], alignment="center"))
                
                # Tarih Filtresi
                mdrop = ft.Dropdown(width=80, value=State.rep_month, options=[ft.dropdown.Option(str(i)) for i in range(1,13)], on_change=lambda e: [setattr(State, 'rep_month', e.control.value), render()])
                ydrop = ft.Dropdown(width=100, value=State.rep_year, options=[ft.dropdown.Option(str(i)) for i in range(2024,2030)], on_change=lambda e: [setattr(State, 'rep_year', e.control.value), render()])
                main_area.controls.append(ft.Row([mdrop, ydrop], alignment="center"))

                # TIKLANABİLİR ÖZET KARTLAR (3'LÜ YAPI)
                def open_detay(tip):
                    State.detail_type = tip
                    State.view = "DetayGoster"
                    render()

                stats_row = ft.Row([
                    ft.Container(
                        content=ft.Column([ft.Text("CİRO", size=10, color="black"), ft.Text(f"₺{ciro:,.0f}", weight="bold", color="black")], alignment="center"),
                        bgcolor=ACCENT, padding=10, border_radius=10, expand=True, on_click=lambda _: open_detay("Ciro"), ink=True
                    ),
                    ft.Container(
                        content=ft.Column([ft.Text("GİDER", size=10, color="white"), ft.Text(f"₺{gider:,.0f}", weight="bold", color="white")], alignment="center"),
                        bgcolor=DANGER, padding=10, border_radius=10, expand=True, on_click=lambda _: open_detay("Gider"), ink=True
                    ),
                    ft.Container(
                        content=ft.Column([ft.Text("NET KASA", size=10, color="white"), ft.Text(f"₺{net_kasa:,.0f}", weight="bold", color="white")], alignment="center"),
                        bgcolor=ACCENT_SEC, padding=10, border_radius=10, expand=True, on_click=lambda _: open_detay("Kasa"), ink=True
                    ),
                ], spacing=10)
                main_area.controls.append(stats_row)
                main_area.controls.append(ft.Text("Detay görmek için kutulara tıklayın", size=10, color=TEXT_SEC, italic=True, text_align="center"))

                # ANA MENÜ GRID
                menu_grid = ft.Column([
                    ft.Container(height=10),
                    ft.Text("Hızlı İşlemler", weight="bold", size=16),
                    ft.Row([
                        ft.Container(content=ft.Column([ft.Icon(ft.Icons.SEND, color=ACCENT, size=30), ft.Text("Sevkiyat", weight="bold")], alignment="center"), bgcolor=CARD_BG, padding=20, border_radius=12, expand=True, on_click=lambda _: go_to("Sevkiyatlar")),
                        ft.Container(content=ft.Column([ft.Icon(ft.Icons.INVENTORY, color=ACCENT_SEC, size=30), ft.Text("Stok", weight="bold")], alignment="center"), bgcolor=CARD_BG, padding=20, border_radius=12, expand=True, on_click=lambda _: go_to("Stok")),
                    ]),
                    ft.Row([
                        ft.Container(content=ft.Column([ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=WARNING, size=30), ft.Text("Kasa", weight="bold")], alignment="center"), bgcolor=CARD_BG, padding=20, border_radius=12, expand=True, on_click=lambda _: go_to("Kasa")),
                        ft.Container(content=ft.Column([ft.Icon(ft.Icons.RECEIPT_LONG, color=DANGER, size=30), ft.Text("Giderler", weight="bold")], alignment="center"), bgcolor=CARD_BG, padding=20, border_radius=12, expand=True, on_click=lambda _: go_to("Giderler")),
                    ]),
                    ft.Row([
                        ft.Container(content=ft.Column([ft.Icon(ft.Icons.PEOPLE, color=TEXT_MAIN, size=30), ft.Text("Müşteriler", weight="bold")], alignment="center"), bgcolor=CARD_BG, padding=20, border_radius=12, expand=True, on_click=lambda _: go_to("Müşteriler")),
                        ft.Container(content=ft.Column([ft.Icon(ft.Icons.LOCAL_SHIPPING, color=TEXT_SEC, size=30), ft.Text("Tedarikçiler", weight="bold")], alignment="center"), bgcolor=CARD_BG, padding=20, border_radius=12, expand=True, on_click=lambda _: go_to("Tedarikçiler")),
                    ])
                ], spacing=10)
                main_area.controls.append(menu_grid)

            # >>>> DETAY GÖSTERME EKRANI (YENİ) <<<<
            elif State.view == "DetayGoster":
                search = f".{State.rep_month.zfill(2)}.{State.rep_year}"
                main_area.controls.append(ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to("AnaMenu")), ft.Text(f"{State.detail_type} Detayları", size=20, weight="bold")], spacing=10))
                
                rows = supabase.table("islemler").select("*").execute().data
                # Filtreleme Mantığı
                if State.detail_type == "Ciro":
                    target_rows = [r for r in rows if search in (r['tarih'] or "") and r['islem_turu'] == "Satis"]
                    clr = ACCENT
                elif State.detail_type == "Gider":
                    target_rows = [r for r in rows if search in (r['tarih'] or "") and r['islem_turu'] == "Gider"]
                    clr = DANGER
                else: # Kasa
                    target_rows = [r for r in rows if search in (r['tarih'] or "") and r['islem_turu'] in ["Tahsilat", "Odeme"]]
                    clr = ACCENT_SEC
                
                if not target_rows:
                    main_area.controls.append(ft.Text("Bu ay için kayıt bulunamadı.", color=TEXT_SEC))
                else:
                    for r in target_rows[::-1]: # Eskiden yeniye
                        main_area.controls.append(mobile_list_item(
                            r['cari_isim'], 
                            f"{r['tarih']} | {r['model_adi'] or r['aciklama'] or '-'}",
                            f"₺{r['toplam_tutar']:,.2f}", 
                            r['islem_turu'], 
                            clr
                        ))

            # >>>> LİSTELER <<<<
            elif State.view in ["Müşteriler", "Tedarikçiler", "Stok", "Sevkiyatlar", "Giderler"]:
                main_area.controls.append(ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to("AnaMenu")), ft.Text(State.view, size=24, weight="bold"), ft.Container(width=40)], alignment="spaceBetween"))
                
                if State.view == "Sevkiyatlar": page.floating_action_button = ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=lambda _: open_form(), bgcolor=ACCENT)
                elif State.view == "Giderler": page.floating_action_button = ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=lambda _: open_form(), bgcolor=DANGER)
                elif State.view == "Stok": page.floating_action_button = ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=lambda _: open_stok_giris(), bgcolor=ACCENT_SEC)
                elif State.view in ["Müşteriler", "Tedarikçiler"]: page.floating_action_button = ft.FloatingActionButton(icon=ft.Icons.PERSON_ADD, on_click=lambda _: open_cari_dlg(), bgcolor=ACCENT)

                try:
                    if State.view == "Sevkiyatlar":
                        res = supabase.table("islemler").select("*").eq("islem_turu", "Satis").order("id", desc=True).limit(50).execute().data
                        for r in res: main_area.controls.append(mobile_list_item(r['cari_isim'], f"İrs: {r['irsaliye_no']} | {r['tarih']}", f"₺{r['toplam_tutar']:,.2f}", "", ACCENT, on_delete=lambda e, x=r: delete_item(x)))
                    elif State.view == "Stok":
                        res = supabase.table("stok").select("*").order("id", desc=True).limit(50).execute().data
                        for r in res: main_area.controls.append(mobile_list_item(r['model_adi'], f"{r['musteri_isim']} | {r['gelis_tarihi']}", f"{r['adet']} Adet", "", TEXT_MAIN))
                    elif State.view in ["Müşteriler", "Tedarikçiler"]:
                        tbl = "musteriler" if State.view == "Müşteriler" else "tedarikciler"
                        res = supabase.table(tbl).select("*").execute().data
                        for r in res:
                            bal = r['bakiye'] or 0
                            main_area.controls.append(mobile_list_item(r['isim'], "Cari Bakiye", f"₺{bal:,.2f}", "", ACCENT if bal >= 0 else DANGER, on_delete=lambda e, id=r['id']: delete_cari(id, tbl)))
                except Exception as ex: main_area.controls.append(ft.Text(f"Hata: {ex}", color=DANGER))

            # >>>> KASA <<<<
            elif State.view == "Kasa":
                main_area.controls.append(ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to("AnaMenu")), ft.Text("Kasa", size=24, weight="bold"), ft.Container(width=40)], alignment="spaceBetween"))
                def set_kasa_mode(m): State.kasa_modu = m; render()
                main_area.controls.append(ft.Row([
                    ft.Container(content=ft.Text("TAHSİLAT", color="black"), bgcolor=ACCENT if State.kasa_modu=="Tahsilat" else "#333", padding=10, border_radius=10, expand=True, on_click=lambda _: set_kasa_mode("Tahsilat"), alignment=ft.alignment.center),
                    ft.Container(content=ft.Text("ÖDEME", color="white"), bgcolor=DANGER if State.kasa_modu=="Odeme" else "#333", padding=10, border_radius=10, expand=True, on_click=lambda _: set_kasa_mode("Odeme"), alignment=ft.alignment.center)
                ]))
                
                kcari = ft.Dropdown(label="Cari Seç", options=[], bgcolor=BG_COLOR, border_radius=10)
                ktutar = ft.TextField(label="Tutar", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=BG_COLOR, border_radius=10)
                try:
                    tbl = "musteriler" if State.kasa_modu == "Tahsilat" else "tedarikciler"
                    kcari.options = [ft.dropdown.Option(str(c['id']), c['isim']) for c in supabase.table(tbl).select("id,isim").execute().data]
                except: pass

                def kaydet_kasa(e):
                    if not kcari.value or not ktutar.value: show_snack("Eksik!", DANGER); return
                    try:
                        t = float(ktutar.value)
                        cname = [x.text for x in kcari.options if x.key==kcari.value][0]
                        supabase.table("islemler").insert({"cari_id": int(kcari.value), "cari_isim": cname, "cari_tip": tbl, "tarih": datetime.now().strftime("%d.%m.%Y"), "toplam_tutar": t, "islem_turu": State.kasa_modu, "aciklama": "Mobil İşlem"}).execute()
                        update_balance(tbl, int(kcari.value), -t if State.kasa_modu=="Tahsilat" else t)
                        show_snack("Kaydedildi"); render()
                    except Exception as ex: show_snack(f"Hata: {ex}")
                main_area.controls.append(create_card(ft.Column([kcari, ktutar, ft.ElevatedButton("ONAYLA", on_click=kaydet_kasa, bgcolor=WARNING, color="black")])))
                res = supabase.table("islemler").select("*").in_("islem_turu", ["Tahsilat", "Odeme"]).order("id", desc=True).limit(20).execute().data
                for r in res: main_area.controls.append(mobile_list_item(r['cari_isim'], f"{r['islem_turu']} | {r['tarih']}", f"₺{r['toplam_tutar']:,.2f}", "", ACCENT if r['islem_turu']=="Tahsilat" else DANGER))

            # >>>> FORM <<<<
            elif State.view == "FORM":
                def on_cari_change(e):
                    if State.view_cache == "Sevkiyatlar":
                        stk = supabase.table("stok").select("model_adi,adet").eq("musteri_id", cdrop.value).execute().data
                        fmdrop.options = [ft.dropdown.Option(s['model_adi']) for s in stk]
                        fmdrop.disabled = False; page.update()
                cdrop.on_change = on_cari_change
                main_area.controls.append(ft.Column([
                    ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to(State.view_cache)), ft.Text(f"YENİ İŞLEM", size=20, weight="bold")]),
                    create_card(ft.Column([cdrop, firs, ffat, fmdrop if State.view_cache=="Sevkiyatlar" else fmtxt, tevdrop if State.view_cache=="Sevkiyatlar" else ft.Container(), ft.Divider(), rows_cont, ft.ElevatedButton("KALEM EKLE", on_click=add_item_row, bgcolor=BG_COLOR, color="white"), ft.Divider(), ft.Row([ft.Text("TOPLAM:", color=TEXT_SEC), totallbl], alignment="spaceBetween"), ft.ElevatedButton("KAYDET", on_click=save_full_form, bgcolor=ACCENT, color="black", width=400)]))
                ]))

            page.update()

        # --- AÇILIR PENCERELER ---
        def open_form():
            State.view_cache = State.view; State.view = "FORM"; State.items_list = []; rows_cont.controls.clear()
            totallbl.value = "₺0.00"
            tbl = "musteriler" if State.view_cache == "Sevkiyatlar" else "tedarikciler"
            try: cdrop.options = [ft.dropdown.Option(str(c['id']), c['isim']) for c in supabase.table(tbl).select("id,isim").execute().data]
            except: pass
            add_item_row(None)
            render()

        def open_stok_giris():
            mc = ft.Dropdown(label="Müşteri", options=[ft.dropdown.Option(str(c['id']), c['isim']) for c in supabase.table("musteriler").select("id,isim").execute().data])
            md = ft.TextField(label="Model"); ad = ft.TextField(label="Adet", keyboard_type="number")
            def save_stok(e):
                supabase.table("stok").insert({"musteri_id": mc.value, "musteri_isim": [x.text for x in mc.options if x.key==mc.value][0], "model_adi": md.value, "adet": int(ad.value), "gelis_tarihi": datetime.now().strftime("%d.%m.%Y")}).execute()
                page.close(page.dialog); show_snack("Stok Girildi"); render()
            page.dialog = ft.AlertDialog(title=ft.Text("Stok Giriş"), content=ft.Column([mc,md,ad], height=200), actions=[ft.ElevatedButton("Kaydet", on_click=save_stok)]); page.open(page.dialog)

        def open_cari_dlg():
            nm = ft.TextField(label="İsim/Ünvan")
            def save_cari(e):
                tbl = "musteriler" if State.view == "Müşteriler" else "tedarikciler"
                supabase.table(tbl).insert({"isim": nm.value, "bakiye": 0}).execute()
                page.close(page.dialog); show_snack("Kişi Eklendi"); render()
            page.dialog = ft.AlertDialog(title=ft.Text("Yeni Cari Ekle"), content=nm, actions=[ft.ElevatedButton("Kaydet", on_click=save_cari)]); page.open(page.dialog)

        # --- GİRİŞ EKRANI ---
        login_email = ft.TextField(label="E-Posta", bgcolor=CARD_BG, border_radius=10, prefix_icon=ft.Icons.EMAIL)
        login_pass = ft.TextField(label="Şifre", password=True, bgcolor=CARD_BG, border_radius=10, prefix_icon=ft.Icons.LOCK)
        remember_me = ft.Checkbox(label="Beni Hatırla", value=False, fill_color=ACCENT)

        if page.client_storage.contains_key("saved_email"):
            login_email.value = page.client_storage.get("saved_email")
            login_pass.value = page.client_storage.get("saved_pass")
            remember_me.value = True
        
        def handle_login(e):
            try:
                supabase.auth.sign_in_with_password({"email": login_email.value, "password": login_pass.value})
                if remember_me.value:
                    page.client_storage.set("saved_email", login_email.value)
                    page.client_storage.set("saved_pass", login_pass.value)
                else:
                    page.client_storage.remove("saved_email")
                    page.client_storage.remove("saved_pass")

                page.clean()
                page.add(ft.Container(content=main_area, expand=True, padding=10))
                render()
            except: show_snack("Giriş Başarısız!", DANGER)

        login_cont = ft.Container(content=ft.Column([
            ft.Text("SIZE TEKSTİL", size=30, weight="bold", color=ACCENT),
            login_email, login_pass, remember_me,
            ft.ElevatedButton("GİRİŞ YAP", on_click=handle_login, bgcolor=ACCENT, color="black", width=200, height=50)
        ], alignment="center", horizontal_alignment="center", spacing=20), alignment=ft.alignment.center, expand=True)

        page.add(login_cont)

    init_app_interface("personel")

ft.app(target=main)