import telebot
from telebot import types
import json
import random
import time
import threading
import os
import string
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


BOT_TOKEN = "8948845798:AAHfpllLg7l5vlgVaaGiEtkWc_XSdyTxs5s"


ADMIN_IDS = [8527221373]

STATUS_CHANNELS = [1003967827684]

REQUIRED_CHANNELS = [
    {
        "id": -1003851566893,
        "link": "https://t.me/furkanstorehack",
        "name": "H1LE GİRİŞ KANALI"
    },
    {
        "id": -1004295705802,
        "link": "https://t.me/furkanstoreguvence",
        "name": "H!LE GUVENCE KANALI"
    },
    {
        "id": -1003967827684,
        "link": "https://t.me/FurkanStorePromosyon",
        "name": "PROMOSYON KODU KANALI"
    }
]


pending_captcha = {}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
DB_FILE = "sms_panel_v7.json"

xox_games = {}
user_msg_times = {}
BAD_WORDS = ["amkOgluqokqna", "aevip", "oçvip", "orospunine", "piç99119", "sikerimjswkwk", "siktirsjwkwk", "yarrakanajaj", "yavşakjaqjqk", "pezevenkajajqj", "götoşajqkqk", "amkuzajakak", "kuzwjakak"]


default_products = {}

def load_database():
    if not os.path.exists(DB_FILE):
        default = {
            "users": {}, "groups": {},
            "stats": {"total_spent": 0, "total_orders": 0, "start_date": str(datetime.now())},
            "logs": [], "gift_codes": {}, "bot_status": "active",
            "products": default_products,
            "categories": {"genel": " Genel"}
        }
        with open(DB_FILE, "w", encoding="utf-8") as f: 
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default

    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "gift_codes" not in data: data["gift_codes"] = {} 
        if "bot_status" not in data: data["bot_status"] = "active"
        if "groups" not in data: data["groups"] = {}
        if "products" not in data: data["products"] = default_products
        if "categories" not in data: data["categories"] = {"genel": " Genel"}
        
        for gid, gdata in list(data["groups"].items()):
            if isinstance(gdata, str): 
                data["groups"][gid] = {"title": gdata, "lang": "tr", "warnings": {}}
        return data

db = load_database()

def save_database(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_user_exists(uid, ref_id=None):
    uid = str(uid)
    
    if uid in db["users"]:
        if "language" not in db["users"][uid]: db["users"][uid]["language"] = None
        if "is_banned" not in db["users"][uid]: db["users"][uid]["is_banned"] = False
        if "order_history" not in db["users"][uid]: db["users"][uid]["order_history"] = []
        if "last_bonus_time" not in db["users"][uid]: db["users"][uid]["last_bonus_time"] = 0
        return
        
    db["users"][uid] = {
        "balance": 0, 
        "is_premium": False, 
        "is_banned": False,
        "refs": 0, 
        "orders_count": 0, 
        "order_history": [],
        "last_bonus_time": 0, 
        "reg_date": str(datetime.now()), 
        "language": None,
        "status": "pending"
    }
    
    if ref_id and str(ref_id) != uid:
        db["users"][uid]["pending_ref"] = str(ref_id)
        
    save_database(db)
    
    
def award_referral(uid, ref_id):
    uid = str(uid); ref_id = str(ref_id)
    if ref_id in db["users"] and ref_id != uid:
        db["users"][ref_id]["balance"] += 1
        db["users"][ref_id]["refs"] += 1
        save_database(db)
        try: bot.send_message(int(ref_id), "<tg-emoji emoji-id=\"6325717349257187998\">💎</tg-emoji> <b>Tebrikler!</b> Davet linkinizle yeni bir üye katıldı, +1 Puan kazandınız!")
        except: pass

def is_member_of_channels(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
        
    if not REQUIRED_CHANNELS: 
        return True
        
    for ch in REQUIRED_CHANNELS:
        if not ch.get("id") or not ch.get("link"):
            continue
        try:
            status = bot.get_chat_member(ch["id"], user_id).status
            if status in ["left", "kicked"]: 
                return False
        except Exception as e:
            print(f"Kanal kontrol hatası ({ch.get('name')}): {e}")
            return False
    return True

def get_channel_join_keyboard():
    markup = InlineKeyboardMarkup()
    
    for ch in REQUIRED_CHANNELS:
        if not ch.get("id") or not ch.get("link"):
            continue
        if "button" in ch:
            markup.row(ch["button"])
        else:
            markup.row(
                pbtn(ch["name"], emoji_id="5188481279963715781", url=ch["link"], style="success")
            )
            
    markup.row(
        pbtn(" Katıldım, Kontrol Et", "check_channels", emoji_id="6325541629260206557", style="success")
    )
    
    return markup
    
    
def send_math_captcha(chat_id, uid, ref_id=None):
    a = random.randint(1, 20); b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])
    operators = {"+": lambda x, y: x + y, "-": lambda x, y: x - y, "*": lambda x, y: x * y}
    answer = operators[op](a, b)
    pending_captcha[str(uid)] = {"answer": answer, "ref": str(ref_id) if ref_id else None}
    msg = bot.send_message(chat_id, f"<tg-emoji emoji-id=\"5296369303661067030\">🔒</tg-emoji> <b>Güvenlik Doğrulaması</b>\n\nBot girişi için aşağıdaki matematik sorusunu çözün:\n\n<code>{a} {op} {b} = ?</code>\n\n<i>Yanlış cevap verirseniz tekrar sorulacak.</i>")
    bot.register_next_step_handler(msg, verify_captcha_step, uid)
def verify_captcha_step(m, uid):
    uid = str(uid)
    if uid not in pending_captcha:
        return
    try:
        girilen = int(m.text.strip())
        dogru = pending_captcha[uid]["answer"]
        ref_id = pending_captcha[uid]["ref"]
        if girilen == dogru:
            del pending_captcha[uid]
            if REQUIRED_CHANNELS and not is_member_of_channels(m.from_user.id):
                bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6242353099193718277\">📣</tg-emoji> <b>Bota erişmek için aşağıdaki kanallara katılman gerekiyor!</b>\nKatıldıktan sonra  butona bas <tg-emoji emoji-id=\"6222198028854367391\">👇</tg-emoji>", reply_markup=get_channel_join_keyboard())
                db["users"][uid]["pending_ref"] = ref_id
                save_database(db)
                return
            if ref_id:
                award_referral(uid, ref_id)
            kb, txts = get_main_keyboard(uid)
            bot.send_message(m.chat.id, f"✅ <b>Doğrulama Başarılı!</b>\n\n{txts['welcome']}", reply_markup=kb)
        else:
            bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6224185666704511761\">❌</tg-emoji> Yanlış cevap! Tekrar dene:")
            send_math_captcha(m.chat.id, uid, ref_id)
    except ValueError:
        bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6224185666704511761\">❌</tg-emoji> Lütfen sadece rakam gir!")
        send_math_captcha(m.chat.id, uid, pending_captcha[uid]["ref"])
    for admin in ADMIN_IDS:
        try: bot.send_message(admin, text)
        except: pass

def notify_admins_with_markup(text, markup):
    for admin in ADMIN_IDS:
        try: bot.send_message(admin, text, reply_markup=markup)
        except: pass

def notify_everyone(status_msg):
    for ch_id in STATUS_CHANNELS:
        try: 
            bot.send_message(ch_id, status_msg)
            time.sleep(0.5) 
        except: pass
    for user_id in db.get("users", {}):
        try: 
            bot.send_message(int(user_id), status_msg)
            time.sleep(0.1) 
        except: pass
        
def create_colored_button(text: str, callback_data: str = None, color: str = "primary", url: str = None):
    """Telegram resmi renkli buton sistemi"""
    style_map = {
        "blue": "primary",
        "green": "success",
        "red": "danger",
        "primary": "primary",
        "success": "success",
        "danger": "danger",
    }

    button_style = style_map.get(color)

    kwargs = {}
    if callback_data:
        kwargs["callback_data"] = callback_data
    if url:
        kwargs["url"] = url

    try:
        if button_style:
            return InlineKeyboardButton(text, style=button_style, **kwargs)
    except TypeError:
        pass

    return InlineKeyboardButton(text, **kwargs)

def animated_loading(chat_id, final_text, markup=None):
    msg = bot.send_message(chat_id, "<tg-emoji emoji-id=\"6235771761892270039\">🔼</tg-emoji> <i>Sistem başlatılıyor...</i>")
    frames = [
        "<tg-emoji emoji-id=\"5981091707456851997\">⏳</tg-emoji> <b>Güvenli bağlantı kuruluyor...</b>\n[▰▱▱▱▱▱▱▱▱▱] 10%",
        "<tg-emoji emoji-id=\"5818775306974006843\">🌐</tg-emoji> <b>Şifreli tünel açılıyor...</b>\n[▰▰▰▰▱▱▱▱▱▱] 40%",
        "<tg-emoji emoji-id=\"6235482220966977551\">🙂</tg-emoji> <b>VIP Sunucuya bağlanılıyor...</b>\n[▰▰▰▰▰▰▰▱▱▱] 70%",
        "<tg-emoji emoji-id=\"6237621131860253190\">✅</tg-emoji> <b>İşlem tamamlanıyor...</b>\n[▰▰▰▰▰▰▰▰▰▰] 100%"
    ]
    for frame in frames:
        time.sleep(0.7) 
        try: bot.edit_message_text(frame, chat_id, msg.message_id)
        except: pass
    time.sleep(0.5)
    try: bot.edit_message_text(final_text, chat_id, msg.message_id, reply_markup=markup)
    except: pass
def animated_premium_upgrade(chat_id, final_text):
    msg = bot.send_message(chat_id, "<tg-emoji emoji-id=\"6235771761892270039\">🔼</tg-emoji> <i>Premium protokolü başlatılıyor...</i>")
    frames = [
        "<tg-emoji emoji-id=\"6235280963094453556\">☄️</tg-emoji> <b>VIP Yetkiler tanımlanıyor...</b>\n[▰▰▰▱▱▱▱▱▱▱]",
        "<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <b>Premium rozeti parlatılıyor...</b>\n[▰▰▰▰▰▰▱▱▱▱]",
        "<tg-emoji emoji-id=\"6237533909664405996\">🕯</tg-emoji> <b>Sistem VIP moda geçiriliyor...</b>\n[▰▰▰▰▰▰▰▰▰▱]",
        "<tg-emoji emoji-id=\"6123126147086556656\">🥇</tg-emoji> <b>İşlem Başarılı!</b>\n[▰▰▰▰▰▰▰▰▰▰]"
    ]
    for frame in frames:
        time.sleep(0.7) 
        try: bot.edit_message_text(frame, chat_id, msg.message_id)
        except: pass
    time.sleep(0.5)
    try: bot.edit_message_text(final_text, chat_id, msg.message_id)
    except: pass

def show_premium_profile(chat_id, msg_id, final_text, markup):
    try:
        bot.edit_message_text("<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <i>VIP Sistemine Bağlanılıyor...</i>", chat_id, msg_id)
        time.sleep(0.5)
        bot.edit_message_text("<tg-emoji emoji-id=\"6237621131860253190\">✅</tg-emoji> <i>Premium Ayrıcalıkları Kontrol Ediliyor...</i>", chat_id, msg_id)
        time.sleep(0.5)
        bot.edit_message_text(final_text, chat_id, msg_id, reply_markup=markup)
    except: pass

def get_main_keyboard(uid):
    try:
        lang = db["users"][str(uid)].get("language", "tr")
        user_balance = db["users"][str(uid)]["balance"]
    except:
        lang = "tr"
        user_balance = 0

    current_hour = datetime.now().hour
    if 6 <= current_hour < 19:
        greet_tr, greet_en = "<tg-emoji emoji-id=\"5402477260982731644\">☀️</tg-emoji> Günaydın", "<tg-emoji emoji-id=\"5402477260982731644\">☀️</tg-emoji> Good morning"
    else:
        greet_tr, greet_en = "<tg-emoji emoji-id=\"5402477260982731644\">☀️</tg-emoji> İyi geceler", "<tg-emoji emoji-id=\"5897561886404120587\">🌛</tg-emoji> Good night"
    
    all_texts = {
        "tr": {
            "profile": " Profilim", "bonus": " Günlük Bonus", "referral": " Davet Et Kazan",
            "leaderboard": " Lider Top 10", "premium": " Premium Ayrıcalığı", "otp_group": " Gurup", "otp_admin": " Admin ",
            "redeem": " Promosyon Kodu", "lang": " Dil Değiştir", "support": " 7/24 Destek",
            "shopping": " VIP Mağaza", "orders": " Sipariş Geçmişi", "transfer": " Puan Transferi",
            "admin_panel": " YÖNETİM MERKEZİ",
            "welcome": f"{greet_tr}!\n <b>Dijital Alışveriş Merkezine Hoşgeldiniz!</b>\nLütfen yapmak istediğiniz işlemi seçiniz:",
            "refund_btn": " Bakiye İadesi", "balance_btn": " Bakiye: {} Puan"
        },
        "en": {
            "profile": " My Profile", "bonus": " Daily Bonus", "referral": " Invite & Earn",
            "leaderboard": " Top 10 Leaders", "premium": " Premium Status", "otp_group": " Group", "otp_admin": " Admin ",
            "redeem": " Promo Code", "lang": " Language", "support": " 24/7 Support",
            "shopping": " VIP Store", "orders": " Order History", "transfer": " Point Transfer",
            "admin_panel": " ADMIN CENTER",
            "welcome": f"{greet_en}!\n <b>Welcome to Digital Hub!</b>\nPlease select an operation:",
            "refund_btn": " Refund Request", "balance_btn": " Balance: {} Pts"
        }
    }
    
def pbtn(text, callback_data=None, emoji_id=None, url=None, style=None):
    if url:
        btn = types.InlineKeyboardButton(text=text, url=url)
    else:
        btn = types.InlineKeyboardButton(text=text, callback_data=callback_data)
    
    try:
        if style:
            btn.style = style
    except:
        pass
        
    try:
        if emoji_id:
            btn.icon_custom_emoji_id = emoji_id
    except:
        pass
        
    return btn


def get_main_keyboard(uid):
    try:
        lang = db["users"][str(uid)].get("language", "tr")
        user_balance = db["users"][str(uid)]["balance"]
    except:
        lang = "tr"
        user_balance = 0

    current_hour = datetime.now().hour
    if 6 <= current_hour < 19:
        greet_tr, greet_en = "<tg-emoji emoji-id=\"5402477260982731644\">☀️</tg-emoji> Günaydın", "<tg-emoji emoji-id=\"5402477260982731644\">☀️</tg-emoji> Good morning"
    else:
        greet_tr, greet_en = "<tg-emoji emoji-id=\"5402477260982731644\">☀️</tg-emoji> İyi geceler", "<tg-emoji emoji-id=\"5897561886404120587\">🌛</tg-emoji> Good night"
    
    all_texts = {
        "tr": {
            "profile": " Profilim", "bonus": " Günlük Bonus", "referral": " Davet Et Kazan",
            "leaderboard": " Lider Top 10", "premium": " Premium Ayrıcalığı", "otp_group": " Gurup", "otp_admin": " Admin ",
            "redeem": " Promosyon Kodu", "lang": " Dil Değiştir", "support": " 7/24 Destek",
            "shopping": " VIP Mağaza", "orders": " Sipariş Geçmişi", "transfer": " Puan Transferi",
            "admin_panel": " YÖNETİM MERKEZİ",
            "welcome": f"{greet_tr}!\n <b>Dijital Alışveriş Merkezine Hoşgeldiniz!</b>\nLütfen yapmak istediğiniz işlemi seçiniz:",
            "refund_btn": " Bakiye İadesi", "balance_btn": " Bakiye: {} Puan"
        },
        "en": {
            "profile": " My Profile", "bonus": " Daily Bonus", "referral": " Invite & Earn",
            "leaderboard": " Top 10 Leaders", "premium": " Premium Status", "otp_group": " Group", "otp_admin": " Admin ",
            "redeem": " Promo Code", "lang": " Language", "support": " 24/7 Support",
            "shopping": " VIP Store", "orders": " Order History", "transfer": " Point Transfer",
            "admin_panel": " ADMIN CENTER",
            "welcome": f"{greet_en}!\n <b>Welcome to Digital Hub!</b>\nPlease select an operation:",
            "refund_btn": " Refund Request", "balance_btn": " Balance: {} Pts"
        }
    }
    
    texts = all_texts.get(lang, all_texts["tr"])
    markup = types.InlineKeyboardMarkup()
    
    markup.row(
        pbtn(texts["profile"], callback_data="nav_profile", emoji_id="4967667085606912536", style="success"), 
        pbtn(texts["bonus"], callback_data="nav_bonus", emoji_id="6323088610228703481", style="success")
    )
    
    markup.row(
        pbtn(texts["shopping"], callback_data="nav_shopping", emoji_id="5143290574673019778", style="danger"), 
        pbtn(texts["premium"], callback_data="nav_premium_buy", emoji_id="6003835612283542072", style="danger")
    )
    
    markup.row(
        pbtn(texts["orders"], callback_data="nav_orders", emoji_id="5909003528956812070", style="primary"), 
       pbtn(texts["redeem"], callback_data="nav_redeem", emoji_id="5418010521309815154", style="danger")
    )
    
    markup.row(
        pbtn(texts["referral"], callback_data="nav_referral", emoji_id="5253510310345600737", style="success"), 
        pbtn(texts["leaderboard"], callback_data="nav_leaderboard", emoji_id="5312315739842026755", style="success")
    )
    
    markup.row(
        pbtn("👨‍💻 Geliştirici", emoji_id="5332769714135394894", url="https://t.me/Zevalsiz")
    )
    
    markup.row(
        pbtn(texts["lang"], callback_data="nav_lang", emoji_id="6147492389909961118", style="primary"), 
        pbtn(texts["support"], callback_data="nav_support", emoji_id="5373251851074415873", style="primary")
    )
    
    if int(uid) in ADMIN_IDS:
        markup.row(
            pbtn(texts["admin_panel"], callback_data="adm_dashboard", emoji_id="5818813162815753343", style="success")
        )
        
    markup.row(
        pbtn(texts["refund_btn"], callback_data="nav_refund", emoji_id="5352759161945867747", style="danger")
    )
    
    markup.row(
        pbtn(texts["balance_btn"].format(user_balance), callback_data="nav_profile", emoji_id="5215420556089776398", style="primary")
    )
    
    return markup, texts
    

def get_admin_keyboard():
    markup = types.InlineKeyboardMarkup()
    
    markup.row(
        pbtn(" Kullanıcı Banla", callback_data="adm_ban_user", emoji_id="5314504236132747481"),
        pbtn(" Ban Kaldır", callback_data="adm_unban_user", emoji_id="5818813162815753343")
    )
    
    markup.row(
        pbtn(" Ürün Ekle", callback_data="adm_add_product", emoji_id="6205984948218762570"),
        pbtn(" Ürün Sil", callback_data="adm_del_product", emoji_id="5314504236132747481")
    )
    
    markup.row(
        pbtn(" Toplu Ürün Sil", callback_data="adm_del_all_products", emoji_id="5314504236132747481")
    )
    
    markup.row(
        pbtn(" Kategori Ekle", callback_data="adm_add_category", emoji_id="6205984948218762570"),
        pbtn(" Kategori Sil", callback_data="adm_del_category", emoji_id="5314504236132747481")
    )
    
    markup.row(
        pbtn(" Premium VIP Ver", callback_data="adm_give_prem", emoji_id="6005862519019673214"),
        pbtn(" Premium VIP Sil", callback_data="adm_take_prem", emoji_id="5314504236132747481")
    )
    
    markup.row(
        pbtn(" Puan Tanımla (Ekle)", callback_data="adm_add_balance", emoji_id="5443127283898405358"),
        pbtn(" Puan Sil", callback_data="adm_sub_balance", emoji_id="5314504236132747481")
    )
    
    markup.row(
        pbtn(" Herkese Toplu Duyuru", callback_data="adm_broadcast", emoji_id="5818813162815753343"),
        pbtn(" Bottan Özel Mesaj", callback_data="adm_send_msg", emoji_id="5463071837427431838")
    )
    
    markup.row(
        pbtn(" Kupon Kodu Oluştur", callback_data="adm_create_gift", emoji_id="5947230838130218401"),
        pbtn(" Tüm Kullanıcıları Listele", callback_data="adm_list_users", emoji_id="5116382939571028928")
    )
    
    markup.row(
        pbtn(" Analiz Raporu", callback_data="adm_stats", emoji_id="5888824471225111740"),
        pbtn(" Sistem Durumu", callback_data="adm_bot_status", emoji_id="6325541629260206557")
    )
    
    markup.row(
        pbtn(" DB Yedekle", callback_data="adm_get_db", emoji_id="6206343625232619150"),
        pbtn(" Son Loglar", callback_data="adm_view_logs", emoji_id="6224381573047783580")
    )
    
    markup.row(
        pbtn(" DB Sıfırla", callback_data="adm_reset_db", emoji_id="5314504236132747481"),
        pbtn(" Çıkış", callback_data="nav_main", emoji_id="5463071837427431838")
    )
    
    return markup


def get_language_keyboard():
    markup = types.InlineKeyboardMarkup()
    
    markup.row(
        pbtn(" Türkçe", callback_data="lang_tr", emoji_id="5985763094276611276"),
        pbtn(" English", callback_data="lang_en", emoji_id="5956225444540847358")
    )
    markup.row(
        pbtn(" Ana Merkeze Dön", callback_data="nav_main", emoji_id="5253997076169115797")
    )
    
    return markup
    
    
def draw_xox_board(chat_id):
    game = xox_games[chat_id]
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(text=cell, callback_data=f"xox_{i}") for i, cell in enumerate(game["board"])]
    markup.add(*buttons)
    return markup

def check_xox_winner(board):
    win_cond = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in win_cond:
        if board[a] == board[b] == board[c] and board[a] != "⬜": return board[a]
    if "⬜" not in board: return "BERABERE"
    return None

@bot.callback_query_handler(func=lambda call: True)
def process_callbacks(call):
    uid = str(call.from_user.id)
    chat_id = call.message.chat.id
    
    if call.message.chat.type != 'private': 
        return
        
    check_user_exists(uid)

    if db.get("bot_status", "active") != "active" and int(uid) not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🛠️ Sistem Bakımda/Kapalı!", show_alert=True)
        return

    if db["users"].get(uid, {}).get("is_banned") and int(uid) not in ADMIN_IDS: 
        bot.answer_callback_query(call.id, "⚠️ Erişiminiz engellenmiştir!", show_alert=True)
        return

    if call.data == "check_channels":
        import time
        time.sleep(0.5)
        
        try:
            üye = is_member_of_channels(call.from_user.id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Kontrol hatası: {e}", show_alert=True)
            return
            
        if üye:
            db["users"][uid]["status"] = "active"
            
            ref_id = db["users"].get(uid, {}).get("pending_ref")
            if not ref_id and "pending_ref" in db:
                ref_id = db["pending_ref"].get(uid) or db["pending_ref"].get(int(uid))

            if ref_id:
                award_referral(uid, ref_id)
                
                if "pending_ref" in db["users"].get(uid, {}):
                    db["users"][uid].pop("pending_ref", None)
                if "pending_ref" in db and uid in db["pending_ref"]:
                    db["pending_ref"].pop(uid, None)
                if "pending_ref" in db and int(uid) in db["pending_ref"]:
                    db["pending_ref"].pop(int(uid), None)
                    
            save_database(db)
                
            kb, txts = get_main_keyboard(uid)
            try:
                bot.edit_message_text(f"<tg-emoji emoji-id=\"6237621131860253190\">✅</tg-emoji> <b>Doğrulama Başarılı!</b>\n\n{txts['welcome']}", chat_id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(chat_id, f"<tg-emoji emoji-id=\"6237621131860253190\">✅</tg-emoji> <b>Doğrulama Başarılı!</b>\n\n{txts['welcome']}", reply_markup=kb)
        else:
            bot.answer_callback_query(call.id, "⚠️ Henüz kanalların hepsine katılmadın ya da sistem üyeliğini algılayamadı!", show_alert=True)
        return
        
        
    if call.data == "nav_main":
        kb, txts = get_main_keyboard(uid)
        try:
            bot.edit_message_text(txts['welcome'], chat_id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(chat_id, txts['welcome'], reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if call.data == "nav_profile":
        u = db["users"][uid]
        vip_status_text = "<tg-emoji emoji-id=\"5818711397860642669\">⏺</tg-emoji> Aktif" if u['is_premium'] else "<tg-emoji emoji-id=\"5348514879558926674\">👎</tg-emoji> Pasif"
        txt = (f"<tg-emoji emoji-id=\"5348136664738839786\">👤</tg-emoji> <b>VIP Profil Özeti</b>\n\n"
               f"<tg-emoji emoji-id=\"5974526806995242353\">🆔</tg-emoji> <b>Kullanıcı ID:</b> <code>{uid}</code>\n"
               f"<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <b>Cüzdan Bakiyesi:</b> {u['balance']} Puan\n"
               f"<tg-emoji emoji-id=\"6005862519019673214\">👑</tg-emoji> <b>VIP Statüsü:</b> {vip_status_text}\n"
               f"<tg-emoji emoji-id=\"6034834452843074121\">🤝</tg-emoji> <b>Davet Edilen:</b> {u['refs']} Kişi\n"
               f"<tg-emoji emoji-id=\"5348227245599105972\">💼</tg-emoji> <b>Toplam Sipariş:</b> {u['orders_count']}\n"
               f"<tg-emoji emoji-id=\"5028418466000930064\">📆</tg-emoji> <b>Kayıt Tarihi:</b> {u['reg_date'][:16]}")
        
        markup = InlineKeyboardMarkup()
        markup.row(
            pbtn(" Ana Merkeze Dön", "nav_main", emoji_id="5253997076169115797", style="danger")
        )
        
        if u.get("is_premium"):
            threading.Thread(target=show_premium_profile, args=(chat_id, call.message.message_id, txt, markup)).start()
        else:
            try:
                bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=markup)
            except:
                bot.send_message(chat_id, txt, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if call.data == "nav_orders":
        history = db["users"][uid].get("order_history", [])
        if not history: 
            txt = "<tg-emoji emoji-id=\"6147910582285639579\">#⃣</tg-emoji> <b>Sipariş Geçmişiniz</b>\n\nSistem kayıtlarında herhangi bir işleminiz bulunmuyor."
        else: 
            txt = "<tg-emoji emoji-id=\"5357315181649076022\">📁</tg-emoji> <b>Sipariş Geçmişiniz (Son 15)</b>\n\n" + "\n".join(history)
            
        kb = InlineKeyboardMarkup()
        kb.row(
            pbtn(" Ana Merkeze Dön", "nav_main", emoji_id="5253997076169115797", style="danger")
        )
        try:
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(chat_id, txt, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if call.data == "nav_transfer":
        msg = bot.send_message(chat_id, "<tg-emoji emoji-id=\"5868375062481997528\">🔄</tg-emoji> <b>Puan Transfer Merkezi</b>\n\nLütfen puan göndermek istediğiniz kişinin <b>ID numarasını</b> yazın:")
        bot.register_next_step_handler(msg, transfer_id_step, uid)
        bot.answer_callback_query(call.id)
        return

    if call.data == "nav_shopping":
        categories = db.get("categories", {"genel": " Genel"})
        m = InlineKeyboardMarkup()
        
        cat_list = list(categories.items())
        for i in range(0, len(cat_list), 2):
            row_buttons = []
            cat_key1, cat_name1 = cat_list[i]
            row_buttons.append(pbtn(cat_name1, f"cat_{cat_key1}", emoji_id="6205984948218762570", style="success"))
            
            if i + 1 < len(cat_list):
                cat_key2, cat_name2 = cat_list[i+1]
                row_buttons.append(pbtn(cat_name2, f"cat_{cat_key2}", emoji_id="6205984948218762570", style="success"))
            
            m.row(*row_buttons)
            
        m.row(
            pbtn(" Ana Merkeze Dön", "nav_main", emoji_id="5253997076169115797", style="danger")
        )
        try:
            bot.edit_message_text("<tg-emoji emoji-id=\"5348227245599105972\">💼</tg-emoji> <b>VIP Mağazaya Hoşgeldiniz!</b>\n\nBir kategori seçin:", chat_id, call.message.message_id, reply_markup=m)
        except:
            bot.send_message(chat_id, "<tg-emoji emoji-id=\"5348227245599105972\">💼</tg-emoji> <b>VIP Mağazaya Hoşgeldiniz!</b>\n\nBir kategori seçin:", reply_markup=m)
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("cat_"):
        cat_key = call.data.split("_", 1)[1]
        products = db.get("products", {})
        
        m = InlineKeyboardMarkup()
        has_product = False
        
        for p_key, p_val in products.items():
            if p_val.get("category") == cat_key:
                has_product = True
                stock = p_val.get("stock", 0)
                
                if stock > 0:
                    btn_text = f"🛍️ {p_val['name']} | {p_val['price']} Puan"
                    c_data = f"prod_{cat_key}_{p_key}"
                else:
                    btn_text = f"❌ {p_val['name']} (Tükenmiş)"
                    c_data = "stock_empty"
                    
                m.row(pbtn(btn_text, c_data, style="success"))
                
        m.row(
            pbtn(" Kategorilere Dön", "nav_shopping", emoji_id="5253997076169115797", style="danger")
        )
        
        txt = f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Kategori İçeriği Listeleniyor</b>\n\nLütfen satın almak istediğiniz ürünü seçin:" if has_product else "⚠️ <b>Bu kategoriye ait güncel ürün bulunamadı!</b>"
        
        try:
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=m)
        except:
            bot.send_message(chat_id, txt, reply_markup=m)
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("prod_"):
        parts = call.data.split("_", 2)
        cat_key = parts[1]
        p_key = parts[2]
        
        product = db.get("products", {}).get(p_key)
        if not product:
            bot.answer_callback_query(call.id, "⚠️ Ürün bulunamadı veya silinmiş!", show_alert=True)
            return
            
        txt = (f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Ürün Detayı: {product['name']}</b>\n\n"
               f"<tg-emoji emoji-id=\"5201873447554145566\">💵</tg-emoji> <b>Fiyat:</b> {product['price']} Puan\n"
               f"<tg-emoji emoji-id=\"5332586662629227075\">🗂</tg-emoji> <b>Kalan Stok:</b> {product.get('stock', 0)} Adet\n\n"
               f"<tg-emoji emoji-id=\"6129877938755079600\">📣</tg-emoji> <i>Satın almak için aşağıdaki butonu kullanabilirsiniz. İşlem admin onayından sonra teslim edilir.</i>")
               
        m = InlineKeyboardMarkup()
        m.row(
            pbtn(f"🛒 {product['price']} Puan Karşılığı Al", f"buy_shop_{p_key}", emoji_id="6325541629260206557", style="success")
        )
        m.row(
            pbtn(" Geri Dön", f"cat_{cat_key}", emoji_id="5253997076169115797", style="danger")
        )
        
        try:
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=m)
        except:
            bot.send_message(chat_id, txt, reply_markup=m)
        bot.answer_callback_query(call.id)
        return

    if call.data == "stock_empty":
        bot.answer_callback_query(call.id, "🔴 Bu ürün tükenmiş, yakında yenilenir!", show_alert=True)
        return

    if call.data.startswith("buy_shop_"):
        item = call.data.split("_", 2)[2]
        product = db.get("products", {}).get(item)
        if not product:
            bot.send_message(chat_id, "⚠️ <b>Bu ürün artık stokta yok veya silinmiş.</b>")
            return
            
        stock = product.get("stock", 99)
        if stock <= 0:
            bot.answer_callback_query(call.id, "🔴 Bu ürün tükenmiş!", show_alert=True)
            return
            
        cost = product["price"]
        item_name = product["name"]
        
        if db["users"][uid]["balance"] < cost:
            bot.send_message(chat_id, f"<tg-emoji emoji-id=\"5348514879558926674\">👎</tg-emoji> <b>İşlem Reddedildi!</b>\nBu ayrıcalıklı ürün için <b>{cost} puana</b> ihtiyacınız var.")
            return
            
        db["users"][uid]["balance"] -= cost
        db["users"][uid]["orders_count"] += 1
        db["products"][item]["stock"] = max(0, stock - 1)
        date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        db["users"][uid].setdefault("order_history", []).insert(0, f"[{date_str}] <tg-emoji emoji-id=\"5400090058030075645\">🛒</tg-emoji> {item_name} (-{cost} <tg-emoji emoji-id=\"6325717349257187998\">💎</tg-emoji>)")
        save_database(db)
        
        
        buyer_name = call.from_user.first_name or "Bilinmeyen"
        buyer_uname = f" (@{call.from_user.username})" if call.from_user.username else ""
        final_msg = f"<tg-emoji emoji-id=\"6237621131860253190\">✅</tg-emoji> <b>Talebiniz Başarıyla Alındı!</b>\n\n<tg-emoji emoji-id=\"5348227245599105972\">💼</tg-emoji> <b>Ürün:</b> {item_name}\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <b>Ödenen Tutar:</b> {cost} Puan\n\n<i><tg-emoji emoji-id=\"5981091707456851997\">⏳</tg-emoji> İşleminiz yetkili onayı için sisteme iletildi. Profiliniz en kısa sürede teslimat için güncellenecektir.</i>"
        
        threading.Thread(target=animated_loading, args=(chat_id, final_msg)).start()
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ ONAYLA (TESLİM ET)", callback_data=f"o_app_{uid}_{item}"), 
            InlineKeyboardButton("❌ REDDET (İPTAL)", callback_data=f"o_rej_{uid}_{item}")
        )
        notify_admins_with_markup(f"<tg-emoji emoji-id=\"5348227245599105972\">💼</tg-emoji> <b>YENİ SİPARİŞ!</b>\n\n👤 Kullanıcı: {buyer_name}{buyer_uname}\n🆔 ID: <code>{uid}</code>\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> Ürün: <b>{item_name}</b>", markup)
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("o_app_"):
        if int(uid) not in ADMIN_IDS: 
            return
        parts = call.data.split("_", 3)
        target_uid = parts[2]
        item = parts[3]
        product = db.get("products", {}).get(item)
        item_name = product["name"] if product else item
        admin_name = call.from_user.first_name or "Yönetim"
        
        msg = bot.send_message(chat_id, f"📦 Müşteriye <b>{item_name}</b> gönderiliyor.\nLütfen hesap bilgilerini, şifreyi veya erişim kodunu yazın:\n<i>(İptal için /iptal)</i>")
        original_text = call.message.text
        bot.register_next_step_handler(msg, lambda m: admin_deliver_order_step(m, target_uid, item_name, call.message.message_id, chat_id, admin_name, original_text))
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("o_rej_"):
        if int(uid) not in ADMIN_IDS: 
            return
        parts = call.data.split("_", 3)
        target_uid = parts[2]
        item = parts[3]
        product = db.get("products", {}).get(item)
        cost = product["price"] if product else 0
        item_name = product["name"] if product else item
        admin_name = call.from_user.first_name or "Yönetim"
        
        if target_uid in db["users"]:
            db["users"][target_uid]["balance"] += cost
            date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
            db["users"][target_uid].setdefault("order_history", []).insert(0, f"[{date_str}] ❌ İade: {item_name} (+{cost} 💎)")
            save_database(db)
            
        try:
            bot.edit_message_text(f"{call.message.text}\n\n❌ <b>Durum: {admin_name} Tarafından İPTAL EDİLDİ</b>", chat_id, call.message.message_id)
        except:
            pass
            
        try: 
            bot.send_message(target_uid, f"<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> <b>İşlem İptal Edildi!</b>\n\n<tg-emoji emoji-id=\"5212947303467345789\">📦</tg-emoji> Ürün: <b>{item_name}</b>\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> Harcadığınız <b>{cost} Puan</b> cüzdanınıza iade edilmiştir.")
        except: 
            pass
        bot.answer_callback_query(call.id)
        return

    if call.data == "nav_bonus":
        now = time.time()
        last_bonus = db["users"][uid].get("last_bonus_time", 0)
        if now - last_bonus < 86400:
            kalan_saniye = 86400 - (now - last_bonus)
            saat = int(kalan_saniye // 3600)
            dakika = int((kalan_saniye % 3600) // 60)
            bot.send_message(chat_id, f"<tg-emoji emoji-id=\"5235989279024373566\">🎰</tg-emoji> Sistemin soğuması gerekiyor! Kalan süre: <b>{saat} Saat {dakika} Dakika</b>")
        else:
            bot.send_message(chat_id, "<tg-emoji emoji-id=\"5235989279024373566\">🎰</tg-emoji> <b>Şans çarkı dönüyor... Bol şans!</b>")
            slot_msg = bot.send_dice(chat_id, emoji='🎰')
            
            def process_bonus():
                time.sleep(2.5)
                kazanc = 1
                tebrik_msji = "<tg-emoji emoji-id=\"6325541629260206557\">🔄</tg-emoji> <b>Tebrikler! Kazandınız.</b>"
                if slot_msg.dice.value == 64:
                    kazanc = 5
                    tebrik_msji = "<tg-emoji emoji-id=\"6325541629260206557\">🔄</tg-emoji> <b>EFSANEVİ KAZANÇ (JACKPOT)! 777 YAKALADIN!</b> <tg-emoji emoji-id=\"6325541629260206557\">🔄</tg-emoji>"
                db["users"][uid]["balance"] += kazanc
                db["users"][uid]["last_bonus_time"] = now
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                db["users"][uid].setdefault("order_history", []).insert(0, f"[{date_str}] <tg-emoji emoji-id=\"5235989279024373566\">🎰</tg-emoji> Şans Bonusu (+{kazanc} <tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji>)")
                save_database(db)
                bot.send_message(chat_id, f"{tebrik_msji}\n<tg-emoji emoji-id=\"6325717349257187998\">💎</tg-emoji> Cüzdana Eklenen: <b>+{kazanc} Puan</b>")
                
            threading.Thread(target=process_bonus).start()
        bot.answer_callback_query(call.id)
        return

    if call.data == "nav_referral":
        bot_user = bot.get_me().username
        link = f"https://t.me/{bot_user}?start={uid}"
        
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton(" Ana Merkeze Dön", callback_data="nav_main"))
        
        try:
            bot.edit_message_text(f"<tg-emoji emoji-id=\"6034834452843074121\">🤝</tg-emoji> <b>Davet Et, Kazan!</b>\n\n<tg-emoji emoji-id=\"6147439566107186310\">👇</tg-emoji> Aşağıdaki kişisel linkinizle arkadaşlarınızı sisteme davet edin, her yeni katılımda anında <b>+1 Puan</b> kazanın.\n\n<tg-emoji emoji-id=\"6071278787947925866\">📋</tg-emoji> <b>Sizin Linkiniz:</b>\n<code>{link}</code>", chat_id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(chat_id, f"<tg-emoji emoji-id=\"6034834452843074121\">🤝</tg-emoji> <b>Davet Et, Kazan!</b>\n\n<tg-emoji emoji-id=\"6147439566107186310\">👇</tg-emoji> Aşağıdaki kişisel linkinizle arkadaşlarınızı sisteme davet edin, her yeni katılımda anında <b>+1 Puan</b> kazanın.\n\n<tg-emoji emoji-id=\"6071278787947925866\">📋</tg-emoji> <b>Sizin Linkiniz:</b>\n<code>{link}</code>", reply_markup=kb)
        bot.answer_callback_query(call.id)
        return
        

    elif call.data == "nav_premium_buy":
        if db["users"][uid].get("is_premium"):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(" Ana Merkeze Dön", callback_data="nav_main"))
            bot.edit_message_text("<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> <b>Zaten Premium VIP Statüsündesiniz!</b>", call.message.chat.id, call.message.message_id, reply_markup=kb)
        else:
            txt = "<tg-emoji emoji-id=\"5769547529993588669\">👑</tg-emoji> <b>VIP Premium Ayrıcalıkları:</b>\n\n<tg-emoji emoji-id=\"5823638915055099648\">⚡</tg-emoji> %100 Sipariş Onay Önceliği\n<tg-emoji emoji-id=\"5251684060186569219\">🔔</tg-emoji> 7/24 Kesintisiz VIP Destek\n\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <b>Aktivasyon Bedeli:</b> 10 Puan"
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("💳 Yükselt", callback_data="act_buy_prem"), types.InlineKeyboardButton(" İptal", callback_data="nav_main"))
            bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "act_buy_prem":
        if db["users"][uid].get("is_premium"): bot.send_message(call.message.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> <b>Zaten Premium üyesiniz!</b>")
        elif db["users"][uid]["balance"] >= 10:
            db["users"][uid]["balance"] -= 10
            db["users"][uid]["is_premium"] = True
            date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
            db["users"][uid].setdefault("order_history", []).insert(0, f"[{date_str}] <tg-emoji emoji-id=\"5769547529993588669\">👑</tg-emoji>VIP Premium (-10 <tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji>)")
            save_database(db)
            final_msg = "<tg-emoji emoji-id=\"6235482220966977551\">🙂</tg-emoji> <b>Aramıza Hoşgeldiniz! VIP Statünüz Onaylandı.</b>"
            threading.Thread(target=animated_premium_upgrade, args=(call.message.chat.id, final_msg)).start()
        else: bot.send_message(call.message.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Puan yetersiz.")

    elif call.data == "nav_redeem":
        msg = bot.send_message(call.message.chat.id, "<tg-emoji emoji-id=\"5418010521309815154\">🎫</tg-emoji> <b>Promosyon/Kupon Kodunuzu Giriniz:</b>")
        bot.register_next_step_handler(msg, lambda m: redeem_gift_code(m, uid))

    elif call.data == "nav_lang":
        bot.edit_message_text("<tg-emoji emoji-id=\"5399898266265475100\">🌍</tg-emoji> Lütfen dil tercihinizi yapın:", call.message.chat.id, call.message.message_id, reply_markup=get_language_keyboard())

    elif call.data == "nav_support":
        msg = bot.send_message(call.message.chat.id, "<tg-emoji emoji-id=\"5251684060186569219\">🔔</tg-emoji> <b>7/24 VIP Destek Hattı</b>\n\nLütfen talebinizi detaylı olarak yazın:")
        bot.register_next_step_handler(msg, send_support_message_step, uid)

    elif call.data == "nav_refund":
        history = db["users"][uid].get("order_history", [])[:5]
        hist_txt = "Kayıtlarda harcama bulunamadı." if not history else "\n".join(history)
        msg_text = f"<tg-emoji emoji-id=\"6086980694460861135\">💸</tg-emoji> <b>Bakiye İade Merkezi</b>\n\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <b>Mevcut Bakiyeniz:</b> {db['users'][uid]['balance']} Puan\n\n<tg-emoji emoji-id=\"5258477770735885832\">📄</tg-emoji> <b>Son İşlemleriniz:</b>\n<code>{hist_txt}</code>\n\nİade talep ettiğiniz işlemi yazınız:"
        msg = bot.send_message(call.message.chat.id, msg_text)
        bot.register_next_step_handler(msg, send_refund_message_step, uid)

    elif call.data == "nav_leaderboard":
        sorted_users = sorted(db["users"].items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
        txt = "<tg-emoji emoji-id=\"5893376775781617954\">🏆</tg-emoji> <b>Elit Liderler Tablosu (Top 10)</b>\n\n"
        for i, (user_id, data) in enumerate(sorted_users, 1):
            medal = "<tg-emoji emoji-id=\"6123126147086556656\">🥇</tg-emoji>" if i == 1 else "<tg-emoji emoji-id=\"5251227187335424668\">🥈</tg-emoji>" if i == 2 else "<tg-emoji emoji-id=\"5251282841521647446\">🥉</tg-emoji>" if i == 3 else "🔸"
            txt += f"{medal} ID: {user_id} | <tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> {data['balance']} | <tg-emoji emoji-id=\"6034834452843074121\">🤝</tg-emoji> {data['refs']} Davet\n"
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(" Ana Merkeze Dön", callback_data="nav_main")))
        
    elif int(uid) in ADMIN_IDS and call.data.startswith("adm_"):
        handle_admin_callbacks(call)

    elif call.data.startswith("lang_"):
        lang = call.data.split("_")[1]
        db["users"][uid]["language"] = lang
        save_database(db)
        kb, txts = get_main_keyboard(uid)
        bot.edit_message_text(f"<tg-emoji emoji-id=\"5350572310627632617\">✅</tg-emoji> Dil güncellendi.\n\n{txts['welcome']}", call.message.chat.id, call.message.message_id, reply_markup=kb)

def handle_admin_callbacks(call):
    uid = str(call.from_user.id)
    if int(uid) not in ADMIN_IDS: return

    if call.data == "adm_dashboard":
        bot.edit_message_text("⚙️ <b>Gelişmiş Yönetim Merkezine Hoşgeldiniz:</b>", call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())
    
    elif call.data == "adm_add_category":
        msg = bot.send_message(call.message.chat.id, "📂 <b>Yeni Kategori Ekle</b>\nFormat: <code>kategori_kodu|📦 Kategori Adı</code>\nÖrn: <code>sosyal|📱 Sosyal Medya</code>\n\n⚠️ Kod boşluksuz, küçük harfle olmalı.")
        bot.register_next_step_handler(msg, admin_add_category_step)

    elif call.data == "adm_del_category":
        categories = db.get("categories", {})
        if not categories:
            bot.answer_callback_query(call.id, "⚠️ Hiç kategori yok!", show_alert=True)
            return
        cat_list = list(categories.items())
        lines = [f"<code>{i+1}</code>. {name}  <i>({key})</i>" for i, (key, name) in enumerate(cat_list)]
        msg = bot.send_message(call.message.chat.id, "🗂️ <b>Kategori Silme Paneli</b>\n\nSilmek istediğiniz kategorinin numarasını yazın:\n\n" + "\n".join(lines))
        bot.register_next_step_handler(msg, admin_del_category_step, cat_list)

    elif call.data == "adm_ban_user":
        msg = bot.send_message(call.message.chat.id, "🚫 <b>Banlanacak Kullanıcı ID girin:</b>")
        bot.register_next_step_handler(msg, lambda m: admin_ban_step(m, True))
        
    elif call.data == "adm_unban_user":
        msg = bot.send_message(call.message.chat.id, "🔓 <b>Banı Kaldırılacak Kullanıcı ID girin:</b>")
        bot.register_next_step_handler(msg, lambda m: admin_ban_step(m, False))

    elif call.data == "adm_add_product":
        categories = db.get("categories", {"genel": " Genel"})
        cat_list = "\n".join([f"  <code>{k}</code> → {v}" for k, v in categories.items()])
        msg = bot.send_message(call.message.chat.id, f"🛒 <b>Eklenecek Ürün Bilgilerini Yazın</b>\nFormat: <code>kod|Ürün Adı|Fiyat|Stok|kategori_kodu</code>\nÖrn: <code>netflix|Netflix Premium|15|50|genel</code>\n\n📂 <b>Mevcut Kategoriler:</b>\n{cat_list}")
        bot.register_next_step_handler(msg, admin_add_product_step)

    elif call.data == "adm_del_all_products":
        products = db.get("products", {})
        if not products:
            bot.answer_callback_query(call.id, "⚠️ Mağazada hiç ürün yok!", show_alert=True)
            return
        product_list = list(products.items())
        lines = [f"<code>{i+1}</code>. {data['name']} — 💎{data['price']} Puan | 📦 Stok: {data.get('stock', 99)}"
                 for i, (pk, data) in enumerate(product_list)]
        list_text = ("🗑️ <b>Toplu Ürün Silme Paneli</b>\n\n"
                     "Silmek istediğiniz ürün numaralarını <b>virgülle</b> yazın.\n"
                     "Tümünü silmek için <code>hepsi</code> yazın.\n\n"
                     "Örn: <code>1,3,5</code>\n\n" + "\n".join(lines))
        msg = bot.send_message(call.message.chat.id, list_text)
        bot.register_next_step_handler(msg, admin_del_all_products_step, product_list)

    elif call.data == "adm_del_product":
        products = db.get("products", {})
        if not products:
            bot.answer_callback_query(call.id, "⚠️ Mağazada hiç ürün yok!", show_alert=True)
            return
        product_list = list(products.items())
        lines = [f"<code>{i+1}</code>. {data['name']} — 💎{data['price']} Puan | 📦 Stok: {data.get('stock', 99)}  <i>({pk})</i>"
                 for i, (pk, data) in enumerate(product_list)]
        list_text = "🗑️ <b>Ürün Silme Paneli</b>\n\nAşağıdan silmek istediğiniz ürünün <b>numarasını</b> yazın:\n\n" + "\n".join(lines)
        msg = bot.send_message(call.message.chat.id, list_text)
        bot.register_next_step_handler(msg, admin_del_product_step, product_list)

    elif call.data == "adm_give_prem":
        msg = bot.send_message(call.message.chat.id, "👑 <b>Premium Yapılacak Kullanıcı ID girin:</b>")
        bot.register_next_step_handler(msg, lambda m: admin_premium_step(m, True))

    elif call.data == "adm_take_prem":
        msg = bot.send_message(call.message.chat.id, "❌ <b>Premiumluğu Silinecek Kullanıcı ID girin:</b>")
        bot.register_next_step_handler(msg, lambda m: admin_premium_step(m, False))

    elif call.data == "adm_add_balance":
        msg = bot.send_message(call.message.chat.id, "💎 <b>Puan Eklenecek Kullanıcı ID ve Miktarı Yazın</b>\nFormat: <code>ID|Puan</code>\nÖrn: <code>1234567|50</code>")
        bot.register_next_step_handler(msg, lambda m: admin_balance_step(m, "add"))

    elif call.data == "adm_sub_balance":
        msg = bot.send_message(call.message.chat.id, "🗑️ <b>Puanı Silinecek Kullanıcı ID ve Miktarı Yazın</b>\nFormat: <code>ID|Puan</code>\nÖrn: <code>1234567|20</code>")
        bot.register_next_step_handler(msg, lambda m: admin_balance_step(m, "sub"))

    elif call.data == "adm_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 <b>Tüm Kullanıcılara Gönderilecek Toplu Duyuru Mesajını Yazın:</b>")
        bot.register_next_step_handler(msg, admin_broadcast_step)

    elif call.data == "adm_send_msg":
        msg = bot.send_message(call.message.chat.id, "✉️ <b>Bottan Kullanıcıya Direkt Mesaj Gönderme</b>\nFormat: <code>ID|Mesajınız</code>\nÖrn: <code>1234567|Hesabınız onaylandı.</code>")
        bot.register_next_step_handler(msg, admin_send_msg_step)

    elif call.data == "adm_create_gift":
        msg = bot.send_message(call.message.chat.id, "🎫 <b>Kupon Oluşturma Paneli</b>\nLütfen kuponu aşağıdaki formatta yazın:\nFormat: <code>KodAdı|Puan|Limit</code>\nÖrn: <code>AÇILIŞ|5|10</code>\n\n<tg-emoji emoji-id=\"6147439566107186310\">👇</tg-emoji> Kod adını boş bırakırsanız (sadece <code>Puan|Limit</code> yazarsanız) rastgele bir kod otomatik üretilir.")
        bot.register_next_step_handler(msg, admin_create_gift_step)

    elif call.data == "adm_list_users":
        users = db.get("users", {})
        total = len(users)
        if total == 0:
            bot.answer_callback_query(call.id, "⚠️ Hiç kayıtlı kullanıcı yok!", show_alert=True)
            return
        lines = []
        for i, (uid_key, udata) in enumerate(users.items(), 1):
            premium = "👑" if udata.get("is_premium") else "👤"
            banned = " 🚫" if udata.get("is_banned") else ""
            lines.append(f"{premium} <code>{uid_key}</code> | 💎{udata.get('balance', 0)}{banned}")
        chunks = [lines[i:i+30] for i in range(0, len(lines), 30)]
        bot.send_message(call.message.chat.id, f"👥 <b>Kayıtlı Kullanıcılar — Toplam: {total}</b>")
        for chunk in chunks:
            bot.send_message(call.message.chat.id, "\n".join(chunk))

    elif call.data == "adm_stats":
        total_users = len(db.get("users", {}))
        txt = f"📊 <b>Sistem Analiz Raporu</b>\n\n👥 Toplam Kayıtlı Kullanıcı: {total_users}\n📦 Aktif Stokta Ürün Türü: {len(db.get('products', {}))}"
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())

    elif call.data == "adm_bot_status":
        db["bot_status"] = "maintenance" if db.get("bot_status", "active") == "active" else "active"
        save_database(db)
        bot.answer_callback_query(call.id, f"Sistem Durumu: {db['bot_status'].upper()}", show_alert=True)
        bot.edit_message_text(f"⚙️ Yönetim Paneli\nBot Durumu Değişti: <b>{db['bot_status'].upper()}</b>", call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())

def transfer_id_step(m, sender_uid):
    target_id = m.text.strip()
    if target_id not in db["users"]:
        kb, _ = get_main_keyboard(sender_uid)
        bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Sistemde böyle bir kullanıcı bulunamadı!", reply_markup=kb)
        return
    if target_id == sender_uid:
        bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Kendinize transfer yapamazsınız!")
        return
    msg = bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"5818715087237549366\">👤</tg-emoji> <b>Alıcı ID:</b> <code>{target_id}</code>\n\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> <b>Gönderilecek Miktarı Belirtin:</b>\n<i>(Cüzdan: {db['users'][sender_uid]['balance']} Puan)</i>")
    bot.register_next_step_handler(msg, transfer_amount_step, sender_uid, target_id)

def transfer_amount_step(m, sender_uid, target_id):
    try:
        amt = int(m.text.strip())
        if amt <= 0: raise ValueError
        if db["users"][sender_uid]["balance"] < amt:
            bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Bakiye yetersiz.")
            return
        db["users"][sender_uid]["balance"] -= amt
        db["users"][target_id]["balance"] += amt
        date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        db["users"][sender_uid].setdefault("order_history", []).insert(0, f"[{date_str}] <tg-emoji emoji-id=\"5253742260054409879\">✉️</tg-emoji> Giden: {target_id} (-{amt} <tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji>)")
        db["users"][target_id].setdefault("order_history", []).insert(0, f"[{date_str}] <tg-emoji emoji-id=\"5253742260054409879\">✉️</tg-emoji> Gelen: {sender_uid} (+{amt} <tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji>)")
        save_database(db)
        kb, _ = get_main_keyboard(sender_uid)
        bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"5350572310627632617\">✅</tg-emoji> <b>Transfer Başarılı!</b>\n\n<tg-emoji emoji-id=\"5818715087237549366\">👤</tg-emoji> Alıcı: {target_id}\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> İletilen: {amt} Puan", reply_markup=kb)
        try: bot.send_message(target_id, f"<tg-emoji emoji-id=\"5350572310627632617\">✅</tg-emoji> Hesabınıza <b>+{amt} Puan</b> eklendi!")
        except: pass
    except: bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Lütfen sadece geçerli pozitif rakam girin.")
def admin_ban_step(m, status):
    target = m.text.strip()
    if target in db["users"]:
        db["users"][target]["is_banned"] = status
        save_database(db)
        bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"5350572310627632617\">✅</tg-emoji> Kullanıcı ({target}) Durumu Güncellendi: Banned={status}")
    else: bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Kullanıcı bulunamadı.")

def admin_add_product_step(m):
    try:
        parts = m.text.split("|")
        pk = parts[0].strip(); name = parts[1].strip(); price = int(parts[2].strip())
        stock = int(parts[3].strip()) if len(parts) >= 4 else 99
        category = parts[4].strip() if len(parts) >= 5 else "genel"
        if category not in db.get("categories", {}):
            bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> <code>{category}</code> kategorisi bulunamadı. Önce admin panelden kategori ekleyin.")
            return
        db["products"][pk] = {"name": name, "price": price, "stock": stock, "category": category}
        save_database(db)
        cat_name = db["categories"][category]
        bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"5350572310627632617\">✅</tg-emoji> Ürün eklendi!\n<tg-emoji emoji-id=\"5212947303467345789\">📦</tg-emoji> <b>{name}</b>\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> {price} Puan | <tg-emoji emoji-id=\"5357315181649076022\">📁</tg-emoji> Stok: {stock}\n<tg-emoji emoji-id=\"6147657922244516465\">📂</tg-emoji> Kategori: {cat_name}")
        duyuru = f"<tg-emoji emoji-id=\"5780560530515171033\">🛍</tg-emoji> <b>Yeni Ürün Eklendi!</b>\n\n<tg-emoji emoji-id=\"5212947303467345789\">📦</tg-emoji> Ürün: <b>{name}</b>\n<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> Fiyat: <b>{price} Puan</b>\n<tg-emoji emoji-id=\"6147657922244516465\">📂</tg-emoji> Kategori: {cat_name}\n\nMağazayı ziyaret etmek için /start yazın!"
        threading.Thread(target=notify_everyone, args=(duyuru,)).start()
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Hatalı format.\n<code>{e}</code>")

def admin_add_category_step(m):
    try:
        parts = m.text.split("|", 1)
        key = parts[0].strip().lower().replace(" ", "_")
        name = parts[1].strip() if len(parts) >= 2 else key
        if key in db.get("categories", {}):
            bot.send_message(m.chat.id, f"⚠️ <code>{key}</code> kategorisi zaten mevcut!")
            return
        db.setdefault("categories", {})[key] = name
        save_database(db)
        bot.send_message(m.chat.id, f"✅ Kategori eklendi!\n📂 <b>{name}</b>  <code>({key})</code>")
    except:
        bot.send_message(m.chat.id, "❌ Hatalı format. Örn: <code>sosyal|📱 Sosyal Medya</code>")

def admin_del_category_step(m, cat_list):
    try:
        idx = int(m.text.strip()) - 1
        if idx < 0 or idx >= len(cat_list):
            bot.send_message(m.chat.id, f"❌ Geçersiz numara. 1 ile {len(cat_list)} arasında girin.")
            return
        key, name = cat_list[idx]
        if key == "genel":
            bot.send_message(m.chat.id, "❌ <b>Genel</b> kategorisi silinemez.")
            return
        del db["categories"][key]
        for pk, pdata in db.get("products", {}).items():
            if pdata.get("category") == key:
                db["products"][pk]["category"] = "genel"
        save_database(db)
        bot.send_message(m.chat.id, f"✅ <b>{name}</b> kategorisi silindi.\n⚠️ Bu kategorideki ürünler <b>Genel</b>'e taşındı.")
    except ValueError:
        bot.send_message(m.chat.id, "❌ Lütfen sadece bir numara girin.")

def admin_del_all_products_step(m, product_list):
    try:
        text = m.text.strip().lower()
        if text == "hepsi":
            sayi = len(product_list)
            db["products"] = {}
            save_database(db)
            bot.send_message(m.chat.id, f"✅ Toplam <b>{sayi} ürün</b> mağazadan silindi.")
            return
        numaralar = [int(x.strip()) for x in text.split(",")]
        gecersiz = [n for n in numaralar if n < 1 or n > len(product_list)]
        if gecersiz:
            bot.send_message(m.chat.id, f"❌ Geçersiz numara: {gecersiz}. Lütfen 1 ile {len(product_list)} arasında girin.")
            return
        silinenler = []
        for n in sorted(set(numaralar)):
            pk, data = product_list[n - 1]
            if pk in db.get("products", {}):
                del db["products"][pk]
                silinenler.append(f"<b>{data['name']}</b>")
        save_database(db)
        bot.send_message(m.chat.id, f"✅ {len(silinenler)} ürün silindi:\n" + "\n".join(silinenler))
    except ValueError:
        bot.send_message(m.chat.id, "❌ Hatalı format. Örn: <code>1,3,5</code> ya da <code>hepsi</code>")

def admin_del_product_step(m, product_list):
    try:
        idx = int(m.text.strip()) - 1
        if idx < 0 or idx >= len(product_list):
            bot.send_message(m.chat.id, f"❌ Geçersiz numara. Lütfen 1 ile {len(product_list)} arasında bir sayı girin.")
            return
        pk, data = product_list[idx]
        if pk in db.get("products", {}):
            del db["products"][pk]
            save_database(db)
            bot.send_message(m.chat.id, f"✅ <b>#{idx+1} — {data['name']}</b> ürünü mağazadan başarıyla silindi.")
        else:
            bot.send_message(m.chat.id, "❌ Ürün artık mevcut değil, silinmiş olabilir.")
    except ValueError:
        bot.send_message(m.chat.id, "❌ Lütfen sadece bir numara girin. (Örn: <code>3</code>)")

def admin_premium_step(m, status):
    target = m.text.strip()
    if target in db["users"]:
        db["users"][target]["is_premium"] = status
        save_database(db)
        bot.send_message(m.chat.id, f"✅ Kullanıcı ({target}) Premium VIP durumu: {status}")
        try: bot.send_message(target, "<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> VIP Premium üyeliğiniz yetkili tarafından güncellendi!" if status else "<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> VIP Premium üyeliğiniz sonlandırıldı.")
        except: pass
    else: bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> Kullanıcı bulunamadı.")

def admin_balance_step(m, mode):
    try:
        target, amt = m.text.split("|")
        target = target.strip(); amt = int(amt.strip())
        if target in db["users"]:
            if mode == "add": db["users"][target]["balance"] += amt
            else: db["users"][target]["balance"] = max(0, db["users"][target]["balance"] - amt)
            save_database(db)
            yeni_bakiye = db["users"][target]["balance"]
            bot.send_message(m.chat.id, f"✅ İşlem Başarılı! {target} yeni bakiyesi: {yeni_bakiye}")
            try: bot.send_message(int(target), f"<tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> Hesabınıza yönetim tarafından <b>{amt} puan</b> eklendi!" if mode == "add" else f"<tg-emoji emoji-id=\"4958534924278694938\">🗑</tg-emoji> Hesabınızdan yönetim tarafından <b>{amt} puan</b> silindi.")
            except: pass
            if mode == "add":
                notify_admins(f"💰 <b>BAKİYE YÜKLEMESİ YAPILDI</b>\n👤 Kullanıcı ID: <code>{target}</code>\n💎 Eklenen: <b>{amt} Puan</b>\n📊 Yeni Bakiye: <b>{yeni_bakiye} Puan</b>")
        else: bot.send_message(m.chat.id, "❌ Kullanıcı bulunamadı.")
    except: bot.send_message(m.chat.id, "❌ Hatalı format.")

def admin_broadcast_step(m):
    text = m.text
    threading.Thread(target=notify_everyone, args=(text,)).start()
    bot.send_message(m.chat.id, "📢 Toplu duyuru işlemi arka planda başlatıldı!")

def admin_send_msg_step(m):
    try:
        target, msg_text = m.text.split("|", 1)
        target = target.strip()
        bot.send_message(int(target), f"<tg-emoji emoji-id=\"5253742260054409879\">✉️</tg-emoji> <b>Yönetimden Gelen Mesaj:</b>\n\n{msg_text.strip()}", parse_mode="HTML")
        bot.send_message(m.chat.id, f"✅ Mesaj <code>{target}</code> kullanıcısına başarıyla iletildi.")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Mesaj gönderilemedi.\n<code>{e}</code>\n\nFormat: <code>ID|Mesajınız</code>")

def admin_create_gift_step(m):
    try:
        parts = [p.strip() for p in m.text.split("|")]

        if len(parts) == 3:
            custom_code, puan, limit = parts
            code = custom_code.upper().replace(" ", "_")
            if not code:
                bot.send_message(m.chat.id, "❌ Kod adı boş olamaz.")
                return
        elif len(parts) == 2:
            puan, limit = parts
            code = "DexYamCap-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        else:
            raise ValueError("format hatası")

        puan = int(puan); limit = int(limit)

        if "gift_codes" not in db: db["gift_codes"] = {}

        if code in db["gift_codes"]:
            bot.send_message(m.chat.id, f"❌ <b>{code}</b> kodu zaten mevcut. Farklı bir kod adı seçin.")
            return

        db["gift_codes"][code] = {"puan": puan, "limit": limit, "used_by": []}
        save_database(db)
        bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"5418010521309815154\">🎫</tg-emoji> <b>Kupon Başarıyla Üretildi!</b>\n\n<tg-emoji emoji-id=\"5465443379917629504\">🔓</tg-emoji> Kod: <code>{code}</code>\n💎 Değer: <b>{puan} Puan</b>\n<tg-emoji emoji-id=\"5309901482890382924\">👤</tg-emoji> Kullanım Limiti: <b>{limit} Kişi</b>")
    except: bot.send_message(m.chat.id, "❌ Hatalı format. Örnekteki gibi giriniz:\nKodAdı|Puan|Limit  (Örn: AÇILIŞ|5|10)\nveya\nPuan|Limit  (rastgele kod için, Örn: 15|100)")

@bot.message_handler(content_types=['new_chat_members', 'text'])
def master_message_handler(m):
    if m.chat.type in ['group', 'supergroup']:
        gid = str(m.chat.id)
        db.setdefault("groups", {}).setdefault(gid, {"lang": "tr", "captcha": True})
        if m.new_chat_members:
            for member in m.new_chat_members:
                if member.id == bot.get_me().id: continue
                if db["groups"][gid].get("captcha", True):
                    try:
                        bot.restrict_chat_member(m.chat.id, member.id, can_send_messages=False)
                        bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"6147439566107186310\">👇</tg-emoji> <b>Hoşgeldiniz</b> {member.first_name}!\nDoğrulamak için butona basın:", reply_markup=get_captcha_keyboard(member.id))
                    except: pass
            return
        return

    if m.chat.type == 'private':
        uid = str(m.from_user.id)
        
        if db.get("bot_status", "active") != "active" and m.from_user.id not in ADMIN_IDS:
            bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"5440621591387980068\">🔜</tg-emoji> Sistem bakımda.")
            return
            
        for word in BAD_WORDS:
            if m.text and word in m.text.lower():
                try: bot.delete_message(m.chat.id, m.message_id)
                except: pass
                return

        uid = str(m.from_user.id)
        chat_id = m.chat.id

        ref = None
        if m.text and m.text.startswith("/start"):
            ref = m.text.split()[1] if len(m.text.split()) > 1 else None

        is_new_user = uid not in db.get("users", {})
        check_user_exists(uid, ref)

        if m.text and m.text.startswith("/start"):
            
            if is_new_user or db["users"][uid].get("status") == "pending":
                db["users"][uid]["status"] = "pending"
                save_database(db)
                send_math_captcha(chat_id, uid, ref)
                return
                
            if REQUIRED_CHANNELS and not is_member_of_channels(m.from_user.id):
                bot.send_message(
                    chat_id, 
                    "<tg-emoji emoji-id=\"6242353099193718277\">📣</tg-emoji> <b>Bota erişmek için aşağıdaki kanallara katılman gerekiyor!</b>\n"
                    "Katıldıktan sonra <tg-emoji emoji-id=\"6325541629260206557\">🔄</tg-emoji> butonuna bas <tg-emoji emoji-id=\"6222198028854367391\">👇</tg-emoji>", 
                    reply_markup=get_channel_join_keyboard()
                )
                return
                
            pending = db["users"].get(uid, {}).get("pending_ref")
            if pending:
                award_referral(uid, pending)
                db["users"][uid].pop("pending_ref", None)
                save_database(db)
                
            kb, txts = get_main_keyboard(uid)
            bot.send_message(chat_id, txts['welcome'], reply_markup=kb)
            return

        elif m.text == "/panel" and int(uid) in ADMIN_IDS:
            bot.send_message(chat_id, "⚙️ <b>Yönetim Merkezine Hoşgeldiniz:</b>", reply_markup=get_admin_keyboard())
            return

        else:
            if REQUIRED_CHANNELS and not is_member_of_channels(m.from_user.id):
                bot.send_message(chat_id, "📢 <b>Bota erişmek için aşağıdaki kanallara katılman gerekiyor!</b>", reply_markup=get_channel_join_keyboard())
                return

            kb, txts = get_main_keyboard(uid)
            bot.send_message(chat_id, txts['welcome'], reply_markup=kb)

def admin_deliver_order_step(m, target_uid, item_name, orig_msg_id, admin_chat_id, admin_name, original_text):
    if m.text == "/iptal": 
        bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Teslimat iptal edildi.")
        return
    bot.edit_message_text(f"{original_text}\n\n<tg-emoji emoji-id=\"5309901482890382924\">👤</tg-emoji> <b>Durum: {admin_name} Tarafından TESLİM EDİLDİ</b>", chat_id=admin_chat_id, message_id=orig_msg_id)
    try: bot.send_message(target_uid, f"<tg-emoji emoji-id=\"5251227707026470504\">🎁</tg-emoji> <b>Siparişiniz Teslim Edildi!</b>\n<tg-emoji emoji-id=\"5212947303467345789\">📦</tg-emoji> Ürün: {item_name}\n<tg-emoji emoji-id=\"5465443379917629504\">🔓</tg-emoji> Veri:\n<code>{m.text}</code>")
    except: pass

def send_refund_message_step(m, uid):
    bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6028565819225542441\">✅</tg-emoji> İade talebiniz iletildi.")
    notify_admins(f"💳 <b>İADE TALEBİ!</b>\n👤 ID: <code>{uid}</code>\n📝 Mesaj: {m.text}")

def send_support_message_step(m, uid):
    bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6028565819225542441\">✅</tg-emoji> Mesajınız destek ekibine iletildi.")
    notify_admins(f"🛎️ <b>DESTEK TALEBİ!</b>\n👤 ID: <code>{uid}</code>\n💬 Mesaj: {m.text}")

def redeem_gift_code(m, uid):
    code = m.text.strip().upper().replace(" ", "_")
    if code in db.get("gift_codes", {}):
        coupon = db["gift_codes"][code]
        if uid in coupon.get("used_by", []):
            bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Bu kuponu daha önce zaten kullandınız!")
            return
        if len(coupon.get("used_by", [])) >= coupon["limit"]:
            bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"6221914376329237010\">⚠️</tg-emoji> Bu kuponun maksimum kullanım limiti dolmuş!")
            return
        bonus = coupon["puan"]
        db["users"][uid]["balance"] += bonus
        coupon.setdefault("used_by", []).append(uid)
        if len(coupon["used_by"]) >= coupon["limit"]:
            del db["gift_codes"][code]
        save_database(db)
        bot.send_message(m.chat.id, f"<tg-emoji emoji-id=\"5418010521309815154\">🎫</tg-emoji> <b>Kupon Başarılı!</b> Hesabınıza <b>+{bonus} Puan</b> <tg-emoji emoji-id=\"5251562950698759162\">💎</tg-emoji> başarıyla eklendi.")
    else: 
        bot.send_message(m.chat.id, "<tg-emoji emoji-id=\"5348514879558926674\">👎</tg-emoji> Geçersiz, süresi dolmuş, kullanılmış veya hatalı kupon kodu.")

if __name__ == '__main__':
    print("🚀 Gelişmiş Kanalsız & Kupon Modlu sürüm stabil modda başlatılıyor...")
    bot.infinity_polling()
