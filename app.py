import streamlit as st
import pandas as pd
import datetime
import time
from datetime import timedelta
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 🟢 เพิ่มการ import ไลบรารี GPS (ต้องใส่ใน requirements.txt ก่อนนะ)
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    st.error("⚠️ ยังไม่ได้ติดตั้ง 'streamlit-js-eval' ใน requirements.txt")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 📧 EMAIL CONFIGURATION
# ==========================================
# ⚠️ สำคัญ: ต้องเป็น Gmail ที่เปิด App Password แล้ว
SENDER_EMAIL = "kitibodee28@gmail.com"  # 🔴 แก้เป็นเมลที่สมัครไว้
SENDER_PASSWORD = "vwfj mask pwfi cpur"      # 🔴 แก้เป็นรหัส App Password 16 หลัก

def send_email_notification(to_emails, subject, body_html):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(to_emails) # รองรับส่งหาหลายคน
        msg['Subject'] = subject

        msg.attach(MIMEText(body_html, 'html')) # ใช้ HTML เพื่อจัดรูปแบบสวยๆ

        # เชื่อมต่อ Server Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_emails, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}") # ดู Log ใน Terminal ถ้าส่งไม่ได้
        return False

import requests
import base64

# 🔑 ใส่ API Key ของ ImgBB ตรงนี้
IMGBB_API_KEY = "d44961a07e3958d0383c5d529805f57f"

def upload_image_to_imgbb(image_file):
    """ฟังก์ชันอัปโหลดรูปเข้า ImgBB แล้วส่งลิงก์กลับมา"""
    try:
        url = "https://api.imgbb.com/1/upload"
        
        # เตรียมข้อมูลสำหรับส่ง
        payload = {
            "key": IMGBB_API_KEY,
            "expiration": 0 # 0 = เก็บถาวร (หรือใส่เลขวินาทีถ้าอยากให้ลบอัตโนมัติ)
        }
        
        # แปลงไฟล์รูปเพื่อส่ง
        files = {
            "image": image_file.getvalue()
        }
        
        # ยิงไปที่ ImgBB
        response = requests.post(url, data=payload, files=files)
        
        if response.status_code == 200:
            result = response.json()
            return result['data']['url'] # ได้ลิงก์รูปกลับมา
        else:
            st.error(f"ImgBB Error: {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return None

# ==========================================
# ⚙️ CONFIG & SECURITY
# ==========================================
st.set_page_config(layout="wide", page_title="TTT Mini ERP", initial_sidebar_state="expanded")

st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)

SHEET_NAME = "TTT_DB"
UPLOAD_FOLDER = "report_images"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 🔐 ข้อมูลผู้ใช้งาน
USERS = {
    "kitibodee": {"pass": "Qaqcpti67", "role": "Admin", "name": "Kitibodee"},
    "jitpanu": {"pass": "Jitpanu@ttt_2026", "role": "GM", "name": "Jitpanu"},
    "theerapon": {"pass": "Theer@pon_01", "role": "CCO", "name": "Theeraphol"},
    "chaiyakit": {"pass": "Chaiyakit2026", "role": "Sale-CO", "name": "Chaiyakit"},
    "nattapong": {"pass": "Mix@pti2024", "role": "Sale", "name": "Nattapong"},
    "samanan": {"pass": "Samanan@nan07", "role": "Sale", "name": "Samanan"},
    "suksun": {"pass": "Suksun@ttt2026", "role": "Sale", "name": "Suksun"},
    "wutthipong": {"pass": "pom@2499", "role": "Sale", "name": "Wutthipong"},
    "podjana": {"pass": "Podjana@sale002", "role": "Sale", "name": "Pojana"},
    "siva": {"pass": "Siva@sale_ttt2026", "role": "Sale", "name": "Siva"},
    "sale04": {"pass": "S@le04", "role": "Sale", "name": "Sale04"},
    "vichai": {"pass": "Vichai2026", "role": "WH", "name": "Vichai"}
}

# ==========================================
# ☁️ GOOGLE SHEETS CONNECTION
# ==========================================
@st.cache_resource
def get_thai_now():
    """ฟังก์ชันดึงเวลาปัจจุบันแบบไทย (UTC+7)"""
    return datetime.datetime.now() + timedelta(hours=7)
def get_gsheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google ไม่ได้: {e}")
        return None

def get_data(worksheet_name):
    client = get_gsheet_client()
    if client:
        # 🔄 ลองดึงข้อมูล 3 ครั้ง (ถ้าครั้งแรกพลาด ให้ลองใหม่)
        for attempt in range(3):
            try:
                sh = client.open(SHEET_NAME)
                wks = sh.worksheet(worksheet_name)
                data = wks.get_all_records()
                # ถ้าดึงสำเร็จ ส่งข้อมูลกลับทันที
                return pd.DataFrame(data)
            except Exception as e:
                # ถ้าพลาด ให้รอ 1 วินาทีแล้วลองใหม่
                time.sleep(1)
                continue
    # ถ้าลอง 3 รอบแล้วยังไม่ได้จริงๆ ค่อยยอมแพ้
    return pd.DataFrame()

def append_data(worksheet_name, row_list):
    client = get_gsheet_client()
    if client:
        sh = client.open(SHEET_NAME)
        wks = sh.worksheet(worksheet_name)
        wks.append_row(row_list)

def run_query(query_type, **kwargs):
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    
    if query_type == "update_stock":
        wks = sh.worksheet("Inventory")
        cell = wks.find(kwargs['code'])
        if 'new_stock' in kwargs:
            wks.update_cell(cell.row, 4, kwargs['new_stock'])
        if 'remark' in kwargs:
            wks.update_cell(cell.row, 6, kwargs['remark'])

    elif query_type == "update_order_status": 
        # อันนี้สำหรับแก้ทั้งบิล (ของเก่า)
        wks = sh.worksheet("Orders")
        cell_list = wks.findall(str(kwargs['oid']))
        col_status = 10
        for cell in cell_list:
            wks.update_cell(cell.row, col_status, kwargs['status'])

    # 🟢 เพิ่มใหม่: แก้สถานะ "รายสินค้า" (Item by Item)
    elif query_type == "update_order_item_status":
        wks = sh.worksheet("Orders")
        # 1. หาเลขบิลทั้งหมดก่อน
        cell_list = wks.findall(str(kwargs['oid']))
        col_code = 5    # คอลัมน์ E คือ Code
        col_status = 10 # คอลัมน์ J คือ Status
        
        for cell in cell_list:
            # 2. เช็คว่าบรรทัดนี้ใช่สินค้าที่ส่งมาไหม
            # (ดึงค่าจาก Sheet มาเทียบ)
            row_code = wks.cell(cell.row, col_code).value
            if str(row_code).strip() == str(kwargs['code']).strip():
                # 3. ถ้าใช่ ให้อัปเดตสถานะบรรทัดนี้
                wks.update_cell(cell.row, col_status, kwargs['status'])
                break # เจอแล้วหยุดหา (ประหยัดเวลา)

    elif query_type == "update_sale_report":
        wks = sh.worksheet("Sale_Reports")
        cell = wks.find(kwargs['doc_no'])
        if cell:
            row = cell.row
            wks.update_cell(row, 4, kwargs['cust'])
            wks.update_cell(row, 5, kwargs['obj'])
            wks.update_cell(row, 6, kwargs['prob'])
            wks.update_cell(row, 7, kwargs['rem'])
            wks.update_cell(row, 9, kwargs['edit_count'])
            wks.update_cell(row, 10, str(datetime.datetime.now()))
            
def generate_doc_no():
    today = datetime.date.today()
    yy = today.strftime("%y")
    mm = today.strftime("%m")
    prefix = f"SR-{yy}-{mm}-"
    df = get_data("Sale_Reports")
    if df.empty: return f"{prefix}001"
    current_month_docs = df[df['doc_no'].astype(str).str.startswith(prefix)]
    if current_month_docs.empty: return f"{prefix}001"
    try:
        last_doc = current_month_docs['doc_no'].iloc[-1]
        last_run_no = int(last_doc.split("-")[-1])
        new_run_no = last_run_no + 1
    except: new_run_no = 1
    return f"{prefix}{new_run_no:03d}"

def generate_so_no():
    today = datetime.date.today()
    yy = today.strftime("%y")
    mm = today.strftime("%m")
    prefix = f"SO-{yy}-{mm}-"
    df = get_data("Orders")
    if df.empty: return f"{prefix}001"
    so_ids = df[df['id'].astype(str).str.startswith(prefix, na=False)]
    if so_ids.empty: return f"{prefix}001"
    try:
        last_doc = so_ids['id'].iloc[-1] 
        last_run_no = int(last_doc.split("-")[-1])
        new_run_no = last_run_no + 1
    except: new_run_no = 1
    return f"{prefix}{new_run_no:03d}"

def check_password():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['user_id'] = None
        st.session_state['user_name'] = None

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            # 🟢 ส่วนที่เพิ่ม: โชว์โลโก้ตรงกลาง
            if os.path.exists("images.png"):
                st.image("images.png", width=200) # ปรับขนาดเล็กใหญ่ตรงนี้ (200 คือกำลังดี)
                
            st.title("🔐 TTT Login Portal")
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            if st.button("Login", type="primary", use_container_width=True):
                if username in USERS and USERS[username]['pass'] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = username
                    st.session_state['user_role'] = USERS[username]['role']
                    st.session_state['user_name'] = USERS[username]['name']
                    st.rerun()
                else:
                    st.error("Username หรือ Password ไม่ถูกต้อง")
        return False
    return True

def logout():
    st.session_state['logged_in'] = False
    st.rerun()

# ==========================================
# 📝 MODULES
# ==========================================

# 1. SALE REPORT (FINAL STABLE: Cache Data + Pure Key System)
def render_sale_report():
    st.header("📝 Sale Report & Visit Log")

    # --- 🟢 1. Initialize & Cache (คงเดิม: ห้ามแตะ!) ---
    if 'static_df_cust' not in st.session_state:
        st.session_state['static_df_cust'] = get_data("Customers")
    df_cust = st.session_state['static_df_cust']

    state_keys = ['edit_mode', 'edit_data', 'gps_lat', 'gps_lon', 
                  'sel_reg_k', 'sel_prov_k', 'sel_cust_k',
                  'sel_brand_k', 'sel_prod_k', 'comp_price_k', # เพิ่ม key ราคา
                  'img_opt']
    for k in state_keys:
        if k not in st.session_state: st.session_state[k] = None

    if st.session_state['edit_data'] is None: st.session_state['edit_data'] = {}
    if st.session_state['edit_mode'] is None: st.session_state['edit_mode'] = False

    tab1, tab2 = st.tabs(["📸 บันทึกรายงานใหม่", "📂 ประวัติรายงาน"])

    with tab1:
        default_doc = generate_doc_no()
        if st.session_state['edit_mode']:
            default_doc = st.session_state['edit_data'].get('doc_no', default_doc)
            
        is_admin = st.session_state.get('user_role') == 'Admin'
        default_name = st.session_state.get('user_name', '')
        
        st.info(f"📄 เลขที่เอกสาร: {default_doc}")
        sales_name = st.text_input("ชื่อเซลล์", value=default_name, disabled=not is_admin)

        # 🟢 เพิ่มลูกค้าใหม่ (คงเดิม)
        with st.expander("➕ เพิ่มลูกค้าใหม่", expanded=False):
            with st.form("new_c_form"):
                c1, c2 = st.columns(2)
                nm = c1.text_input("ชื่อลูกค้าใหม่")
                rg = c2.selectbox("ภูมิภาค", ["กรุงเทพฯและปริมณฑล", "ภาคกลาง", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคตะวันออก", "ภาคตะวันตก", "ภาคใต้"])
                pl = []
                if not df_cust.empty: pl = sorted(df_cust['Province'].unique().tolist())
                pv = st.selectbox("จังหวัด", pl + ["ระบุเอง"])
                if pv == "ระบุเอง": pv_manual = st.text_input("พิมพ์ชื่อจังหวัด")
                else: pv_manual = pv
                
                if st.form_submit_button("💾 บันทึก"):
                    if nm and pv_manual:
                        r_p = pv_manual if pv == "ระบุเอง" else pv
                        append_data("Customers", [nm.strip(), r_p, rg])
                        del st.session_state['static_df_cust']
                        st.success("เพิ่มสำเร็จ!"); time.sleep(1); st.rerun()
                    else: st.error("กรอกให้ครบ")

        # 🟢 เลือกลูกค้า (คงเดิม)
        st.markdown("### 🏢 ข้อมูลลูกค้า")
        cust_name_final = ""
        if not df_cust.empty:
            c_f1, c_f2, c_sel = st.columns([1, 1, 2])
            
            all_regs = ["- ทั้งหมด -"] + sorted(df_cust['Region'].dropna().unique().tolist())
            reg_val = c_f1.selectbox("1. ภูมิภาค", all_regs, key="sel_reg_k")
            
            df_s1 = df_cust
            if reg_val != "- ทั้งหมด -": df_s1 = df_s1[df_s1['Region'] == reg_val]
            
            all_provs = ["- ทั้งหมด -"] + sorted(df_s1['Province'].dropna().unique().tolist())
            prov_val = c_f2.selectbox("2. จังหวัด", all_provs, key="sel_prov_k")
            
            df_s2 = df_s1
            if prov_val != "- ทั้งหมด -": df_s2 = df_s2[df_s2['Province'] == prov_val]
            
            all_custs = sorted(df_s2['Customer'].dropna().unique().tolist())
            
            # Logic Pre-select for Edit
            if st.session_state['edit_mode'] and st.session_state['edit_data'].get('customer_name'):
                 target = st.session_state['edit_data']['customer_name']
                 if target in all_custs and st.session_state['sel_cust_k'] != target:
                     pass 

            cust_val = c_sel.selectbox("3. ชื่อลูกค้า", all_custs, key="sel_cust_k")
            cust_name_final = cust_val
            
            if cust_val:
                match = df_cust[df_cust['Customer'] == cust_val]
                if not match.empty: st.caption(f"📍 {match.iloc[0]['Province']} | {match.iloc[0]['Region']}")
        else:
            cust_name_final = st.text_input("ชื่อลูกค้า (พิมพ์เอง)", key="manual_cust_key")

        # 🟢 GPS (คงเดิม)
        st.write("---")
        cg1, cg2 = st.columns([1,3])
        with cg1: st.write("📍 **Location**")
        if st.session_state['gps_lat'] is None:
            loc = get_geolocation(component_key='gps_final_v2')
            if loc and 'coords' in loc:
                st.session_state['gps_lat'] = loc['coords']['latitude']
                st.session_state['gps_lon'] = loc['coords']['longitude']
                st.rerun()
        with cg2:
            if st.session_state['gps_lat']: st.success(f"✅ {st.session_state['gps_lat']}, {st.session_state['gps_lon']}")
            else: st.warning("กำลังจับพิกัด...")

        # =========================================================
        # 🟢 ข้อมูลคู่แข่ง + ย้ายราคามาตรงนี้ (3 คอลัมน์)
        # =========================================================
        st.write("---")
        st.write("🕵️ **ข้อมูลคู่แข่ง / ราคาตลาด**")
        
        if 'static_df_comp' not in st.session_state:
            st.session_state['static_df_comp'] = get_data("Competitor_Data")
        df_comp = st.session_state['static_df_comp']
        
        brands = ["- ไม่ระบุ -"]
        if not df_comp.empty: brands += sorted(df_comp['brand'].unique().tolist())
        brands.append("➕ เพิ่มใหม่...")

        # แบ่งเป็น 3 ช่อง: ยี่ห้อ | สินค้า | ราคา
        c_cp1, c_cp2, c_cp3 = st.columns(3)
        
        # 1. ยี่ห้อ
        b_val = c_cp1.selectbox("ยี่ห้อ", brands, key="sel_brand_k")
        f_brand = b_val
        if b_val == "➕ เพิ่มใหม่...": f_brand = c_cp1.text_input("ระบุยี่ห้อ", key="txt_brand_new")

        # 2. สินค้า
        prods = ["- ไม่ระบุ -"]
        if f_brand not in ["- ไม่ระบุ -", "➕ เพิ่มใหม่..."] and not df_comp.empty:
             sub = df_comp[df_comp['brand'] == f_brand]
             prods += sorted(sub['product'].unique().tolist())
        prods.append("➕ เพิ่มใหม่...")
        
        p_val = c_cp2.selectbox("รุ่น/สินค้า", prods, key="sel_prod_k")
        f_prod = p_val
        if p_val == "➕ เพิ่มใหม่...": f_prod = c_cp2.text_input("ระบุสินค้า", key="txt_prod_new")

        # 3. ราคา (ย้ายมานี่แล้ว!)
        old_price = 0.0
        if st.session_state['edit_mode']:
             old_price = float(st.session_state['edit_data'].get('comp_price', 0.0))
        
        # ใช้ Key "comp_price_k" เพื่อให้ค่าไม่หายเวลารีเฟรช
        price_val = c_cp3.number_input("ราคาคู่แข่ง (บาท)", min_value=0.0, step=1.0, value=old_price, key="comp_price_k")

        # 📸 รูปภาพ (คงเดิม)
        st.write("---")
        st.write("📸 **รูปถ่ายหน้างาน**")
        img_src = st.radio("เลือกวิธีแนบรูป:", ["🚫 ไม่แนบ", "📸 กล้อง", "📂 อัปโหลด"], horizontal=True, key="main_img_opt")
        f_img = None
        if img_src == "📸 กล้อง": f_img = st.camera_input("ถ่ายรูป", key="cam_main")
        elif img_src == "📂 อัปโหลด": f_img = st.file_uploader("เลือกไฟล์", key="file_main")

        # =========================================================
        # 🛡️ FORM บันทึก (เอาช่องราคาออกไปแล้ว)
        # =========================================================
        with st.form("final_entry_form"):
            st.info("👇 กรอกข้อมูลแล้วกดบันทึก")
            
            # เวลา
            now_thai = datetime.datetime.now() + datetime.timedelta(hours=7)
            now_clean = now_thai.replace(second=0, microsecond=0)
            
            cd1, cd2, cd3 = st.columns(3)
            d_visit = cd1.date_input("วันที่", now_thai.date())
            t_in = cd2.time_input("เวลาเข้า", value=now_clean.time()) 
            t_out = cd3.time_input("เวลาออก", value=now_clean.time())
            
            objs = st.multiselect("วัตถุประสงค์", ["1.เยี่ยมลูกค้า", "2.เสนอขาย", "3.เก็บเช็ค", "4.แก้ปัญหา", "5.อื่นๆ"])
            
            old_p = st.session_state['edit_data'].get('problem', "") if st.session_state['edit_mode'] else ""
            old_r = st.session_state['edit_data'].get('remark', "") if st.session_state['edit_mode'] else ""
            
            prob = st.text_area("ปัญหา/Feedback", value=old_p, height=100)
            rem = st.text_input("หมายเหตุ", value=old_r)
            
            st.write("---")
            if st.form_submit_button("💾 บันทึกรายงาน", type="primary", use_container_width=True):
                if cust_name_final:
                    # Save Comp
                    if f_brand and f_prod and f_brand not in ["- ไม่ระบุ -"] and f_prod not in ["- ไม่ระบุ -"]:
                         exists = False
                         if not df_comp.empty:
                             match = df_comp[(df_comp['brand']==f_brand) & (df_comp['product']==f_prod)]
                             if not match.empty: exists = True
                         if not exists: 
                             append_data("Competitor_Data", [f_brand, f_prod])
                             if 'static_df_comp' in st.session_state: del st.session_state['static_df_comp']
                    
                    link = ""
                    if f_img:
                        with st.spinner("Uploading..."): link = upload_image_to_imgbb(f_img)
                    
                    ts = str(datetime.datetime.now() + datetime.timedelta(hours=7))
                    row = [
                        default_doc, str(d_visit), sales_name, cust_name_final,
                        ", ".join(objs), prob, rem, link, 0, ts,
                        str(t_in), str(t_out), f_brand, f_prod, 
                        price_val, # ใช้ค่าราคาจากตัวแปรข้างบน
                        str(st.session_state['gps_lat']), str(st.session_state['gps_lon'])
                    ]
                    
                    if st.session_state['edit_mode']:
                        cnt = int(st.session_state['edit_data'].get('edit_count', 0)) + 1
                        run_query("update_sale_report", doc_no=default_doc, cust=cust_name_final, obj=", ".join(objs), prob=prob, rem=rem, edit_count=cnt)
                        st.success("✅ แก้ไขเรียบร้อย"); st.session_state['edit_mode'] = False; st.session_state['edit_data'] = {}
                    else:
                        append_data("Sale_Reports", row)
                        st.success(f"✅ บันทึก: {default_doc}")
                    
                    time.sleep(1); st.rerun()
                else: st.error("⚠️ เลือกชื่อลูกค้าด้วยครับ")

    # ==========================
    # TAB 2: ประวัติ (Safe Mode)
    # ==========================
    with tab2:
        df = get_data("Sale_Reports")
        if not df.empty:
            role = st.session_state.get('user_role', 'Sale')
            uname = st.session_state.get('user_name', '')
            if role == "Sale" and 'sales_person' in df.columns:
                df = df[df['sales_person'] == uname]
            
            df = df.iloc[::-1]
            for i, r in df.iterrows():
                cb = r.get('comp_brand', '-')
                cp = r.get('comp_product', '-')
                cpr = r.get('comp_price', '-')
                info = f"🔴 (Edit {r['edit_count']})" if r.get('edit_count', 0) > 0 else ""
                
                with st.expander(f"📄 {r.get('doc_no','-')} | {r.get('customer_name','-')} {info}"):
                    c_a, c_b = st.columns([4, 1])
                    with c_a:
                        st.write(f"📅 {r.get('date','-')} | 🕒 {r.get('time_in','-')} - {r.get('time_out','-')}")
                        st.write(f"🎯 **วัตถุประสงค์:** {r.get('objective','-')}")
                        st.write(f"🕵️ **คู่แข่ง:** {cb} | {cp} | {cpr}")
                        st.write(f"⚠️ **ปัญหา:** {r.get('problem','-')}")
                        
                        ip = str(r.get('image_path', '')).strip()
                        if ip.startswith("http"): st.image(ip, width=300)
                    
                    with c_b:
                        if r.get('sales_person') == uname or role == 'Admin':
                            if st.button("✏️", key=f"ed_{r.get('doc_no')}"):
                                st.session_state['edit_mode'] = True
                                st.session_state['edit_data'] = r.to_dict()
                                st.rerun()
                         
# 2. STOCK & ORDER (Hybrid: สต็อกเดิม + ตะกร้าใหม่ + ลูกค้าอยู่บน)
def render_stock_order():
    st.header("🛒 ระบบสั่งซื้อ & เช็คสต็อก (Stock & Order)")

    # --- 🟢 1. เตรียมตัวแปร (State) ---
    if 'cart' not in st.session_state:
        st.session_state['cart'] = []

    # --- 🟢 2. โหลดข้อมูล Stock (พร้อมปุ่ม Reset) ---
    df = get_data("Inventory")
    if df.empty:
        st.warning("⚠️ โหลดข้อมูล Stock ไม่สำเร็จ (หรือยังไม่มีสินค้า)")
        if st.button("🔄 กดตรงนี้เพื่อโหลดใหม่ (Refresh)", type="primary"):
            st.rerun()
        return

    # --- 🟢 3. คำนวณยอดจอง (Logic เดิมที่บอสชอบ) ---
    # ต้องดึง Orders มาคำนวณว่ามีคนจองไปเท่าไหร่แล้ว
    df_ord = get_data("Orders")
    if not df_ord.empty:
        # Clean column names
        df_ord.columns = df_ord.columns.str.strip()
        if 'customer_name' not in df_ord.columns and 'customer' in df_ord.columns:
            df_ord.rename(columns={'customer': 'customer_name'}, inplace=True)

    reserved = pd.DataFrame()
    if not df_ord.empty:
        # สถานะที่ถือว่า "จองของ" อยู่
        active_status = ['Pending_Manager', 'Pending_SaleCO', 'Reserved']
        if 'status' in df_ord.columns:
            pending = df_ord[df_ord['status'].isin(active_status)]
            if not pending.empty:
                reserved = pending.groupby('code')['qty'].sum().reset_index()
                reserved.columns = ['code', 'reserved_qty']
    
    # Merge ยอดจองเข้ากับ Stock
    df['code'] = df['code'].astype(str)
    if not reserved.empty:
        reserved['code'] = reserved['code'].astype(str)
        df = pd.merge(df, reserved, on='code', how='left')
    else:
        df['reserved_qty'] = 0
        
    df['reserved_qty'] = df['reserved_qty'].fillna(0)
    df['available'] = df['real_stock'] - df['reserved_qty'] # คงเหลือขายจริง

    # =========================================================
    # 🟢 4. ส่วนข้อมูลลูกค้า (ย้ายมาไว้บนสุด ตามสั่ง!)
    # =========================================================
    st.markdown("### 👤 ข้อมูลการเปิดบิล (Customer Info)")
    
    # เตรียมรายชื่อลูกค้าสำหรับ Dropdown
    df_cust = get_data("Customers")
    cust_list = []
    if not df_cust.empty:
        cust_list = sorted(df_cust['Customer'].unique().tolist())
    
    c_info1, c_info2 = st.columns(2)
    
    # ชื่อเซลล์
    my_name = st.session_state.get('user_name', 'Sales')
    is_admin = st.session_state.get('user_role') == 'Admin'
    sales_name = c_info1.text_input("พนักงานขาย", value=my_name, disabled=not is_admin)
    
    # ชื่อลูกค้า (Dropdown ค้นหาได้)
    # ใช้ key เพื่อจำค่า
    cust_name = c_info2.selectbox("ลูกค้า (Customer)", ["- เลือกลูกค้า -"] + cust_list, key="so_cust_name")

    st.divider()

    # =========================================================
    # 🟢 5. ระบบเลือกสินค้า & ตะกร้า (TAB SYSTEM)
    # =========================================================
    tab1, tab2 = st.tabs(["📦 เลือกสินค้า (Stock)", f"🛒 ตะกร้าสินค้า ({len(st.session_state['cart'])})"])

    # --- TAB 1: เลือกสินค้าจาก Stock ---
    with tab1:
        # Filter หมวดหมู่
        if 'category' in df.columns:
            cats = df['category'].dropna().unique().tolist()
            if cats:
                with st.expander("📂 กรองหมวดหมู่สินค้า"):
                    sel_cats = st.multiselect("เลือกหมวดหมู่:", cats)
                    if sel_cats: df = df[df['category'].isin(sel_cats)]

        # Search Box
        search_txt = st.text_input("🔍 ค้นหาสินค้า (ชื่อหรือรหัส)", placeholder="พิมพ์เพื่อค้นหา...")
        if search_txt:
            mask = df['name'].astype(str).str.contains(search_txt, case=False) | df['code'].astype(str).str.contains(search_txt, case=False)
            df = df[mask]

        # ตารางสินค้า (Interactive)
        st.write("👇 **คลิกที่แถวเพื่อเลือกสินค้า**")
        event = st.dataframe(
            df[['code', 'name', 'real_stock', 'reserved_qty', 'available', 'unit']], 
            column_config={
                "code": "รหัส",
                "name": "ชื่อสินค้า",
                "real_stock": "สต็อกจริง", 
                "reserved_qty": "จองแล้ว", 
                "available": "พร้อมขาย", 
                "unit": "หน่วย"
            },
            use_container_width=True, 
            on_select="rerun", 
            selection_mode="single-row"
        )

        # เมื่อเลือกสินค้า -> โชว์ฟอร์มใส่ตะกร้า
        if event.selection.rows:
            item = df.iloc[event.selection.rows[0]]
            
            st.info(f"✨ คุณเลือก: **{item['name']}** (พร้อมขาย: {item['available']} {item['unit']})")
            
            with st.form("add_cart_form"):
                c_qty, c_type = st.columns(2)
                qty_val = c_qty.number_input(f"จำนวน ({item['unit']})", min_value=1, value=1)
                price_type = c_type.radio("ประเภทราคา", ["Normal (ราคาปกติ)", "Special (ราคาพิเศษ)"])
                
                special_price = 0.0
                if price_type == "Special (ราคาพิเศษ)":
                    special_price = st.number_input("ระบุราคาพิเศษ (บาท/หน่วย)", min_value=0.0)
                    st.warning("⚠️ ราคาพิเศษ: ต้องรอ Manager/GM อนุมัติก่อน")

                if st.form_submit_button("🛒 ใส่ตะกร้า"):
                    # Logic ราคา
                    final_price = special_price if price_type == "Special (ราคาพิเศษ)" else 0.0 # 0.0 หมายถึงให้ไปดึงราคา Master หรือใส่ทีหลัง
                    type_code = "Special" if price_type == "Special (ราคาพิเศษ)" else "Normal"
                    
                    cart_item = {
                        "code": item['code'],
                        "name": item['name'],
                        "qty": qty_val,
                        "unit": item['unit'],
                        "price": final_price,
                        "type": type_code,
                        "total": qty_val * final_price
                    }
                    st.session_state['cart'].append(cart_item)
                    st.success(f"✅ เพิ่ม {item['name']} ลงตะกร้าแล้ว")
                    time.sleep(0.5)
                    st.rerun()

    # --- TAB 2: ตะกร้าสินค้า (แบบใหม่ ลบได้ทีละตัว) ---
    with tab2:
        st.subheader(f"🧾 รายการในตะกร้าของ: {cust_name}")
        
        if st.session_state['cart']:
            # Header
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
            c1.markdown("**สินค้า**")
            c2.markdown("**ราคา**")
            c3.markdown("**จำนวน**")
            c4.markdown("**รวม**")
            c5.markdown("**ลบ**")
            
            idx_to_remove = None
            total_amount = 0
            
            for i, item in enumerate(st.session_state['cart']):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                    p_txt = f"{item['price']:,.2f}" if item['price'] > 0 else "ตามระบบ"
                    t_txt = f"{item['total']:,.2f}" if item['total'] > 0 else "-"
                    
                    col1.write(f"{item['code']} - {item['name']}")
                    col2.write(p_txt)
                    col3.write(f"{item['qty']} {item['unit']}")
                    col4.write(t_txt)
                    
                    if col5.button("🗑️", key=f"del_{i}"):
                        idx_to_remove = i
                
                total_amount += item['total']
            
            if idx_to_remove is not None:
                del st.session_state['cart'][idx_to_remove]
                st.rerun()
                
            st.divider()
            st.write(f"💰 **ยอดรวม (เฉพาะราคาพิเศษ): {total_amount:,.2f} บาท**")
            
            # ปุ่มยืนยัน (อยู่ล่างสุดของตะกร้า)
            if st.button("✅ ยืนยันการสั่งซื้อ (Confirm Order)", type="primary", use_container_width=True):
                if cust_name != "- เลือกลูกค้า -":
                    so_id = generate_so_no()
                    ts = str(datetime.datetime.now() + datetime.timedelta(hours=7))
                    today_str = str(datetime.date.today())
                    
                    # บันทึกลง Sheet
                    for item in st.session_state['cart']:
                        status = "Pending_Manager" if item['type'] == "Special" else "Pending_SaleCO"
                        row = [so_id, today_str, sales_name, cust_name, item['code'], item['qty'], item['price'], item['total'], item['type'], status]
                        append_data("Orders", row)
                    
                    st.success(f"🎉 เปิดบิลสำเร็จ! เลขที่: {so_id}")
                    st.session_state['cart'] = [] # ล้างตะกร้า
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("⚠️ กรุณาเลือกลูกค้าก่อนยืนยันครับ")
        else:
            st.info("🛒 ตะกร้าว่างเปล่า เลือกสินค้าจาก Tab แรกได้เลยครับ")

    st.write("---")

    # =========================================================
    # 🟢 6. ส่วนประวัติ (HISTORY) - แก้เพิ่มชื่อเซลล์ให้แล้วครับ
    # =========================================================
    if 'df_ord' in locals() and not df_ord.empty:
        user_role = st.session_state.get('user_role', 'Sale')
        
        # Filter ตามสิทธิ์
        if user_role in ['Admin', 'GM', 'CCO', 'Sale-CO']:
            hist_df = df_ord.copy()
            title = "📜 ประวัติการเปิดบิลทั้งหมด (All History)"
        else:
            hist_df = df_ord[df_ord['sales_person'] == my_name] if 'sales_person' in df_ord.columns else pd.DataFrame()
            title = "📜 ประวัติการเปิดบิลของฉัน (My History)"

        # แจ้งเตือน Rejected
        if not hist_df.empty and 'status' in hist_df.columns:
            rejected = hist_df[hist_df['status'] == 'Rejected']
            if not rejected.empty:
                st.error(f"❌ มี {len(rejected)} รายการถูกปฏิเสธ (Rejected)")

        with st.expander(title, expanded=True):
            if not hist_df.empty:
                hist_df = hist_df.iloc[::-1] # เรียงใหม่เอาล่าสุดขึ้นก่อน
                
                # ✅ จุดที่แก้: เพิ่ม 'sales_person' เข้าไปในลิสต์นี้
                cols = ['id', 'date', 'sales_person', 'customer_name', 'code', 'qty', 'status', 'type']
                
                # กรองเอาเฉพาะคอลัมน์ที่มีจริงในไฟล์ (กัน Error จอแดง)
                show_cols = [c for c in cols if c in hist_df.columns]
                
                # ทำสี Status
                def color_status(val):
                    c = 'black'
                    if val == 'Rejected': c = 'red'
                    elif val == 'Completed': c = 'green'
                    elif val == 'Pending_Manager': c = 'orange'
                    elif val == 'Cancelled': c = 'gray'
                    return f'color: {c}'

                try:
                    # พยายามโชว์แบบมีสี
                    st.dataframe(
                        hist_df[show_cols].style.applymap(color_status, subset=['status']),
                        use_container_width=True,
                        hide_index=True
                    )
                except:
                    # ถ้าโชว์สีไม่ได้ ให้โชว์ตารางธรรมดา (Safe Mode)
                    st.dataframe(hist_df[show_cols], use_container_width=True)
            else:
                st.caption("ไม่มีรายการ")

# 3. MANAGER APPROVE (Update: อนุมัติ/ไม่อนุมัติ รายการต่อรายการ)
def render_manager():
    st.header("👔 Approval Dashboard")
    
    df = get_data("Orders")
    if df.empty: st.info("ไม่มีข้อมูล"); return
    
    df.columns = df.columns.str.strip()
    
    # Map ชื่อสินค้า
    df_inv = get_data("Inventory")
    if not df_inv.empty:
        df_inv['code'] = df_inv['code'].astype(str)
        code_to_name = dict(zip(df_inv['code'], df_inv['name']))
        df['name'] = df['code'].astype(str).map(code_to_name).fillna("ไม่พบชื่อสินค้า")
    else:
        df['name'] = "-"

    # กรองเฉพาะ Pending_Manager
    pending = df[df['status'] == 'Pending_Manager']
    
    if pending.empty:
        st.success("✅ ไม่มีรายการค้างอนุมัติ")
        return
    
    order_groups = pending.groupby('id')
    
    for oid, items in order_groups:
        sales_person = items.iloc[0]['sales_person'] if 'sales_person' in items.columns else "-"
        customer = items.iloc[0]['customer_name'] if 'customer_name' in items.columns else "-"
        
        with st.expander(f"Order: {oid} | เซลล์: {sales_person} | ลูกค้า: {customer}", expanded=True):
            
            # 🟢 สร้างตารางสำหรับแก้ไข (Data Editor)
            # เพิ่มคอลัมน์ 'Decision' ให้เลือก
            items_to_edit = items.copy()
            items_to_edit['การตัดสินใจ'] = "รอพิจารณา" # ค่าเริ่มต้น
            
            # เลือกคอลัมน์ที่จะแสดง
            cols = ['code', 'name', 'qty', 'unit_price', 'total_price', 'การตัดสินใจ']
            valid_cols = [c for c in cols if c in items_to_edit.columns]
            
            edited_df = st.data_editor(
                items_to_edit[valid_cols],
                column_config={
                    "การตัดสินใจ": st.column_config.SelectboxColumn(
                        "ผลการพิจารณา",
                        options=["✅ อนุมัติ", "❌ ไม่อนุมัติ", "รอพิจารณา"],
                        required=True,
                        width="medium"
                    ),
                    "qty": st.column_config.NumberColumn("จำนวน", disabled=True),
                    "unit_price": st.column_config.NumberColumn("ราคาขอ", disabled=True),
                    "total_price": st.column_config.NumberColumn("รวม", disabled=True)
                },
                hide_index=True,
                key=f"editor_{oid}",
                use_container_width=True
            )
            
            # ปุ่มยืนยัน
            if st.button("💾 บันทึกผลการพิจารณา", key=f"save_{oid}", type="primary"):
                
                # ตัวแปรเก็บรายการเพื่อส่งเมล
                rejected_items = []
                approved_count = 0
                
                # Loop เช็คทีละบรรทัดจากตารางที่แก้แล้ว
                for index, row in edited_df.iterrows():
                    decision = row['การตัดสินใจ']
                    code = row['code']
                    name = row['name']
                    qty = row['qty']
                    price = row['unit_price'] if 'unit_price' in row else 0
                    
                    if decision == "✅ อนุมัติ":
                        run_query("update_order_item_status", oid=oid, code=str(code), status="Pending_SaleCO")
                        approved_count += 1
                        
                    elif decision == "❌ ไม่อนุมัติ":
                        run_query("update_order_item_status", oid=oid, code=str(code), status="Rejected")
                        rejected_items.append(f"<li>{name} (จำนวน: {qty}) - ราคาขอ: {price}</li>")
                
                # --- ส่งเมลแจ้ง Sale-CO เฉพาะรายการที่ "ไม่ผ่าน" ---
                if rejected_items:
                    try:
                        subject = f"❌ แจ้งผล: มีรายการไม่อนุมัติ (Rejected) - {oid}"
                        receivers = ["Chaiyakit@pacifictube.com"]
                        items_html = "".join(rejected_items)
                        
                        body = f"""
                        <p>เรียน คุณชัยกิจ (Sale-CO),</p>
                        <p>จากการพิจารณาออเดอร์ <b>{oid}</b> (เซลล์: {sales_person}) มีรายการที่ <b>"ไม่อนุมัติ"</b> ดังนี้:</p>
                        <ul>{items_html}</ul>
                        <p>ส่วนรายการอื่นๆ (ถ้ามี) ได้รับการอนุมัติเรียบร้อยแล้ว</p>
                        <hr>
                        <p><b>⚠️ สิ่งที่ต้องทำ:</b></p>
                        <p>รบกวน <b>โทรแจ้งเซลล์ ({sales_person})</b> ถึงรายการที่ไม่ผ่านครับ</p>
                        """
                        send_email_notification(receivers, subject, body)
                        st.toast("📧 ส่งเมลแจ้งรายการที่ถูกปัดตกเรียบร้อย")
                    except Exception as e:
                        print(e)
                
                if approved_count > 0 or len(rejected_items) > 0:
                    st.success("✅ บันทึกข้อมูลเรียบร้อย!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("⚠️ กรุณาเลือก 'อนุมัติ' หรือ 'ไม่อนุมัติ' อย่างน้อย 1 รายการ")

# 4. SALE-CO (เหมือนเดิม)
def render_saleco():
    st.header("👩‍💼 Sale-CO: Confirm Reservation")
    st.info("ℹ️ หน้าที่: ตรวจสอบออเดอร์ และกด 'ยืนยันการจอง' เพื่อแจ้ง WH ให้เตรียมของ")
    df = get_data("Orders")
    if df.empty: return
    pending = df[df['status'] == 'Pending_SaleCO']
    if pending.empty: st.success("✅ ไม่มีรายการค้างจอง"); return
    order_groups = pending.groupby('id')
    for oid, items in order_groups:
        with st.expander(f"Order: {oid} | ลูกค้า: {items.iloc[0]['customer_name']}"):
            st.dataframe(items[['code', 'qty', 'status']])
            if st.button("✅ ยืนยันจองของ (Confirm Reserve)", key=f"res_{oid}"):
                run_query("update_order_status", oid=oid, status="Reserved")
                st.success(f"จองของสำหรับออเดอร์ {oid} แล้ว! (รอ WH ตัดสต็อก)")
                time.sleep(1)
                st.rerun()

# 5. WH ADMIN (ฉบับ Final Fix: แก้ประวัติหาย + เพิ่มปุ่มล้างแคชแก้ค้าง)
def render_wh():
    st.header("🏭 Warehouse Management (ผู้จัดการคลัง)")

    # ---------------------------------------------------------
    # 🔴 ปุ่มกู้ชีพ: กดเมื่อข้อมูลไม่มา หรือ อยากรีเฟรชใหม่จริงๆ
    # ---------------------------------------------------------
    if st.button("🧹 ล้างระบบ/อัปเดตข้อมูลล่าสุด (กดเมื่อข้อมูลไม่มา)", type="primary"):
        st.cache_data.clear()
        st.rerun()

    # ---------------------------------------------------------
    # 🟢 1. โหลดข้อมูล Inventory
    # ---------------------------------------------------------
    try:
        df = get_data("Inventory")
    except Exception as e:
        st.warning(f"⚠️ กำลังเชื่อมต่อ Google Sheet... (ถ้าค้างนานให้กดปุ่ม 'ล้างระบบ' ข้างบน): {e}")
        return

    if df.empty:
        st.info("📭 ไม่พบข้อมูลสินค้าใน Stock (หรือกำลังโหลด)")
        return

    # --- Clean Data ---
    try:
        df = df.drop_duplicates(subset=['code'], keep='first')
        df = df[df['code'].astype(str).str.strip() != '']
        df = df[~df['code'].astype(str).str.contains("รวม", na=False)] 
        df['real_stock'] = pd.to_numeric(df['real_stock'], errors='coerce').fillna(0)
        
        # เติมคอลัมน์ที่ขาด (กัน Error)
        for c in ['remark', 'category', 'name', 'unit']: 
            if c not in df.columns: df[c] = ""
    except Exception as e:
        st.error(f"❌ ข้อมูลสินค้าผิดพลาด: {e}")
        return

    # ---------------------------------------------------------
    # 🟢 2. TABS เมนู
    # ---------------------------------------------------------
    tab_dash, tab_ship, tab_adj, tab_add, tab_hist = st.tabs([
        "📊 Dashboard", 
        "🚚 ตัดของส่ง", 
        "🔧 ปรับยอด/รับของ", 
        "➕ เพิ่มสินค้า", 
        "📜 ประวัติ" 
    ])

    # =========================================================
    # TAB 1: DASHBOARD
    # =========================================================
    with tab_dash:
        st.subheader("📈 ภาพรวม (Real-time)")
        c1, c2 = st.columns(2)
        c1.metric("📦 รายการสินค้า", f"{len(df):,}")
        c2.metric("📊 สต็อกคงเหลือ", f"{df['real_stock'].sum():,.0f}")
        
        # ดึงยอดรับ/จ่าย (ใส่ try-except กันพัง)
        with st.expander("📊 ดูยอดเคลื่อนไหวเดือนนี้ (คลิกเพื่อโหลด)", expanded=True):
            try:
                df_log = get_data("WH_Logs")
                if not df_log.empty:
                    df_log['Qty'] = pd.to_numeric(df_log['Qty'], errors='coerce').fillna(0)
                    df_log['Date'] = pd.to_datetime(df_log['Date'], errors='coerce')
                    today = datetime.date.today()
                    this_month = df_log[(df_log['Date'].dt.month == today.month) & (df_log['Date'].dt.year == today.year)]
                    
                    if not this_month.empty:
                        inbound = this_month[this_month['Action'] == 'Stock In']['Qty'].sum()
                        outbound = this_month[this_month['Action'].isin(['Stock Out', 'Ship Order'])]['Qty'].sum()
                        c3, c4 = st.columns(2)
                        c3.metric("📥 รับเข้า", f"{inbound:,.0f}", delta="Inbound")
                        c4.metric("📤 จ่ายออก", f"{outbound:,.0f}", delta="-Outbound", delta_color="inverse")
                    else:
                        st.info("เดือนนี้ยังไม่มีการเคลื่อนไหว")
            except:
                st.warning("⚠️ กำลังโหลดข้อมูล Log...")

    # =========================================================
    # TAB 2: SHIP ORDERS
    # =========================================================
    with tab_ship:
        st.subheader("🚚 รายการรอตัดสต็อก")
        try:
            df_ord = get_data("Orders")
            has_job = False
            if not df_ord.empty and 'status' in df_ord.columns:
                target = ['Reserved', 'Pending_SaleCO', 'Pending_Manager']
                pending = df_ord[df_ord['status'].isin(target)]
                
                if not pending.empty:
                    has_job = True
                    for oid, items in pending.groupby('id'):
                        c_name = items.iloc[0]['customer_name'] if 'customer_name' in items.columns else "-"
                        with st.expander(f"📦 {oid} | {c_name}"):
                            st.dataframe(items[['code', 'qty']], use_container_width=True)
                            c1, c2 = st.columns(2)
                            if c1.button("✂️ ตัดสต็อก", key=f"s_{oid}", type="primary"):
                                for _, r in items.iterrows():
                                    s_row = df[df['code'].astype(str) == str(r['code'])]
                                    if not s_row.empty:
                                        curr = s_row['real_stock'].values[0]
                                        run_query("update_stock", code=str(r['code']), new_stock=int(curr)-int(r['qty']))
                                        append_data("WH_Logs", [str(datetime.datetime.now()), str(datetime.date.today()), "Ship Order", str(r['code']), s_row['name'].values[0], r['qty'], s_row['unit'].values[0], c_name, oid, "System Cut"])
                                run_query("update_order_status", oid=oid, status="Completed")
                                st.success("Success!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                            
                            if c2.button("เคลียร์สถานะ", key=f"c_{oid}"):
                                run_query("update_order_status", oid=oid, status="Completed")
                                st.cache_data.clear(); st.rerun()
                else: st.success("✅ ไม่มีงานค้าง")
            if not has_job: st.info("ว่าง")
        except: st.error("โหลด Order ไม่ได้")

    # =========================================================
    # TAB 3: ปรับยอด (ระบบค้นหาแบบกดปุ่ม = ลื่น)
    # =========================================================
    with tab_adj:
        st.subheader("🔧 ปรับยอด / รับเข้า / ตัดมือ")
        
        # 1. ค้นหา
        with st.form("search_prod"):
            col_s1, col_s2 = st.columns([4, 1])
            search_txt = col_s1.text_input("🔍 ค้นหา (รหัส/ชื่อ)", placeholder="พิมพ์แล้วกดปุ่มค้นหา ->")
            search_btn = col_s2.form_submit_button("🔎 ค้นหา")
        
        if search_btn and search_txt:
            mask = df['code'].astype(str).str.contains(search_txt, case=False) | df['name'].astype(str).str.contains(search_txt, case=False)
            df_show = df[mask]
        else:
            df_show = df.iloc[:5] # โชว์แค่นิดเดียวพอ ไม่โหลดหนัก
            if not search_btn: st.caption("แสดง 5 รายการล่าสุด (พิมพ์เพื่อค้นหาเพิ่ม)")

        # 2. ตารางเลือก
        event = st.dataframe(
            df_show[['code', 'name', 'real_stock', 'unit', 'remark']],
            column_config={"real_stock": "คงเหลือ", "remark": "หมายเหตุ (สินค้า)"},
            on_select="rerun", selection_mode="single-row", use_container_width=True, hide_index=True
        )

        if event.selection.rows:
            idx = event.selection.rows[0]
            item = df_show.iloc[idx]
            st.divider()
            st.info(f"📍 เลือก: **{item['name']}** | คงเหลือ: **{item['real_stock']}** {item['unit']}")

            # 3. Form ปรับยอด
            with st.form("adj_action"):
                col_a1, col_a2 = st.columns(2)
                # ลูกค้า
                df_cust = get_data("Customers")
                cust_list = ["-"] + df_cust['Customer'].tolist() if not df_cust.empty else ["-"]
                c_cust = col_a1.selectbox("ลูกค้า:", cust_list)
                c_cust_txt = col_a1.text_input("หรือระบุเอง:", placeholder="ชื่อลูกค้า...")
                final_cust = c_cust_txt if c_cust_txt else c_cust
                
                # WO / Note
                c_wo = col_a2.text_input("เลข WO / DO:")
                c_note = st.text_input("หมายเหตุ (Note):", placeholder="เช่น ของจริงมี 20 รออีก 80")
                c_qty = st.number_input(f"จำนวน ({item['unit']}):", min_value=0, value=0)
                
                c_btn1, c_btn2 = st.columns(2)
                do_in = c_btn1.form_submit_button("➕ รับเข้า")
                do_out = c_btn2.form_submit_button("➖ จ่ายออก")
                
                if do_in:
                    run_query("update_stock", code=str(item['code']), new_stock=int(item['real_stock'])+c_qty)
                    append_data("WH_Logs", [str(datetime.datetime.now()), str(datetime.date.today()), "Stock In", str(item['code']), item['name'], c_qty, item['unit'], final_cust, c_wo, c_note])
                    st.success("✅ รับเข้าสำเร็จ"); st.cache_data.clear(); time.sleep(1); st.rerun()
                    
                if do_out:
                    if int(item['real_stock']) >= c_qty:
                        run_query("update_stock", code=str(item['code']), new_stock=int(item['real_stock'])-c_qty)
                        append_data("WH_Logs", [str(datetime.datetime.now()), str(datetime.date.today()), "Stock Out", str(item['code']), item['name'], c_qty, item['unit'], final_cust, c_wo, c_note])
                        st.success("✅ จ่ายออกสำเร็จ"); st.cache_data.clear(); time.sleep(1); st.rerun()
                    else:
                        st.error("❌ สต็อกไม่พอ")

    # =========================================================
    # TAB 4: เพิ่มสินค้า
    # =========================================================
    with tab_add:
        st.subheader("➕ เพิ่มสินค้าใหม่")
        with st.form("add_new_prod"):
            c1, c2 = st.columns(2)
            n_code = c1.text_input("รหัส (Code)")
            n_cat = c2.text_input("หมวดหมู่ (Category)")
            n_name = st.text_input("ชื่อสินค้า")
            c3, c4 = st.columns(2)
            n_qty = c3.number_input("จำนวนเริ่ม", 0)
            n_unit = c4.text_input("หน่วย", "ม้วน")
            
            if st.form_submit_button("💾 บันทึก"):
                if n_code and n_name:
                    if n_code in df['code'].values:
                        st.error("รหัสซ้ำ!")
                    else:
                        append_data("Inventory", [n_code, n_cat, n_name, n_qty, n_unit, "New"])
                        st.success("เพิ่มสำเร็จ"); st.cache_data.clear(); time.sleep(1); st.rerun()
                else: st.error("กรอกข้อมูลไม่ครบ")

    # =========================================================
    # TAB 5: ประวัติ (แก้ปัญหาประวัติหาย)
    # =========================================================
    with tab_hist:
        st.subheader("📜 ประวัติ Log")
        try:
            df_log = get_data("WH_Logs")
            
            if not df_log.empty:
                # 1. จัดการคอลัมน์ User vs Customer ให้จบ
                if 'User' in df_log.columns and 'Customer' not in df_log.columns:
                    df_log = df_log.rename(columns={'User': 'Customer'})
                
                # 2. เติมคอลัมน์ WO / Note ถ้าไม่มี (กันพัง)
                req_cols = ['Timestamp', 'Date', 'Action', 'Code', 'Name', 'Qty', 'Unit', 'Customer', 'WO', 'Note']
                for c in req_cols:
                    if c not in df_log.columns: df_log[c] = "" # เติมค่าว่าง

                # 3. เรียงลำดับ
                df_log = df_log.sort_values(by='Timestamp', ascending=False)

                # 4. แสดงผลแบบแก้ไขได้
                edited_df = st.data_editor(
                    df_log[req_cols],
                    column_config={
                        "Timestamp": st.column_config.TextColumn("เวลา", disabled=True),
                        "Code": st.column_config.TextColumn("รหัส (แก้ได้)"),
                        "Name": st.column_config.TextColumn("ชื่อ (Auto)"),
                        "Qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                        "Customer": st.column_config.TextColumn("ลูกค้า", width="medium"),
                        "WO": st.column_config.TextColumn("WO/DO", width="medium"),
                        "Note": st.column_config.TextColumn("หมายเหตุ", width="large"),
                    },
                    hide_index=True, num_rows="fixed", use_container_width=True, key="hist_fix"
                )

                # 5. ปุ่มบันทึก
                if st.button("💾 บันทึกการแก้ไขประวัติ"):
                    # Auto Update Name
                    code_map = dict(zip(df['code'].astype(str), df['name']))
                    edited_df['Name'] = edited_df['Code'].astype(str).map(code_map).fillna(edited_df['Name'])
                    
                    # แปลงเป็น List
                    data_to_write = edited_df.values.tolist()
                    
                    # เขียนลง Sheet (แบบล้างแล้วเขียนใหม่ เพื่อความชัวร์)
                    client = get_gsheet_client()
                    wks = client.open(SHEET_NAME).worksheet("WH_Logs")
                    wks.clear()
                    wks.append_row(req_cols) # เขียนหัวตารางใหม่ (Customer, WO, Note)
                    wks.append_rows(data_to_write)
                    
                    st.success("✅ บันทึกประวัติเรียบร้อย!"); st.cache_data.clear(); time.sleep(1); st.rerun()
            else:
                st.info("ยังไม่มีประวัติ (หรือกดปุ่ม 'ล้างระบบ' ด้านบนเพื่อลองโหลดใหม่)")
        
        except Exception as e:
            st.error(f"⚠️ เกิดข้อผิดพลาดในการโหลดประวัติ: {e}")
            st.button("ลองโหลดใหม่", on_click=st.cache_data.clear)
            
# 6. SUPPORT (เหมือนเดิม)
def render_support():
    st.header("🆘 Support & Nearby Services")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🏨 โรงแรมใกล้ฉัน", "https://www.google.com/maps/search/hotels+near+me", use_container_width=True)
        st.link_button("⛽ ปั๊มน้ำมันใกล้ฉัน", "https://www.google.com/maps/search/gas+station+near+me", use_container_width=True)
    with col2:
        st.link_button("🍽️ ร้านอาหารใกล้ฉัน", "https://www.google.com/maps/search/restaurants+near+me", use_container_width=True)
        st.link_button("🏥 โรงพยาบาลใกล้ฉัน", "https://www.google.com/maps/search/hospitals+near+me", use_container_width=True)

# 7. PRODUCT CATALOGUE (New!)
def render_catalogue():
    st.header("📖 Product Catalogue 2025")
    st.info("ℹ️ เลื่อนลงด้านล่างเพื่อดูรายละเอียดสินค้าทั้งหมด")
    
    # ชื่อไฟล์ต้องตรงกับที่อัปโหลดเป๊ะๆ นะครับ
    image_files = ["1_หน้าปก.jpg", "2_หน้า2.jpg", "3_หน้า3.jpg", "4_หน้า4.jpg"]
    
    for img in image_files:
        if os.path.exists(img):
            st.image(img, use_container_width=True) # ปรับขนาดเต็มจออัตโนมัติ
            st.write("---") # เส้นขีดคั่นแต่ละหน้า
        else:
            st.error(f"❌ ไม่พบไฟล์: {img} (กรุณาตรวจสอบชื่อไฟล์ให้ถูกต้อง)")

# 8. EXECUTIVE DASHBOARD (Update: ตัดเรื่องเงินออก เน้นจำนวนของ)
def render_dashboard():
    st.header("📊 Executive Dashboard (ภาพรวมการทำงาน)")
    
    # 1. ดึงข้อมูล
    df = get_data("Orders")
    if df.empty:
        st.info("ยังไม่มีข้อมูลการขาย")
        return

    # Clean ชื่อคอลัมน์
    df.columns = df.columns.str.strip()
    
    # กรองเฉพาะออเดอร์ที่ "ขายได้จริง"
    valid_status = ['Completed', 'Reserved', 'Pending_SaleCO', 'Pending_Manager'] 
    if 'status' in df.columns:
        df_valid = df[df['status'].isin(valid_status)].copy()
    else:
        st.error("ไม่พบคอลัมน์ 'status' ใน Google Sheet")
        return
    
    if df_valid.empty:
        st.warning("ไม่มียอดขายที่ active ในขณะนี้")
        return

    # แปลงตัวเลข (เน้นแค่ Qty)
    df_valid['qty'] = pd.to_numeric(df_valid['qty'], errors='coerce').fillna(0)
    
    # --- 🟢 KPI CARDS (เน้นปริมาณงาน) ---
    total_orders = df_valid['id'].nunique() # นับจำนวนบิล
    total_items = df_valid['qty'].sum()     # นับจำนวนชิ้นสินค้า
    
    # นับจำนวนบิลเดือนนี้
    today = datetime.date.today()
    month_orders = 0
    if 'date' in df_valid.columns:
        df_valid['date'] = pd.to_datetime(df_valid['date'], errors='coerce')
        this_month = df_valid[df_valid['date'].dt.month == today.month]
        month_orders = this_month['id'].nunique()

    # โชว์แค่ 3 ช่องพอ (ตัดยอดเงินออก)
    c1, c2, c3 = st.columns(3)
    c1.metric("📃 บิลทั้งหมด (Total Orders)", f"{total_orders} ใบ")
    c2.metric("📅 บิลเดือนนี้ (This Month)", f"{month_orders} ใบ")
    c3.metric("📦 สินค้าที่ขายออก (Total Qty)", f"{total_items:,.0f} ชิ้น")
    
    st.divider()

    # --- 🟢 CHARTS (กราฟ) ---
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("🏆 5 สินค้าขายดี (Top Products)")
        # Map ชื่อสินค้า
        df_inv = get_data("Inventory")
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip()
            df_inv['code'] = df_inv['code'].astype(str)
            if 'name' in df_inv.columns:
                code_map = dict(zip(df_inv['code'], df_inv['name']))
                df_valid['product_name'] = df_valid['code'].astype(str).map(code_map).fillna(df_valid['code'])
            else:
                df_valid['product_name'] = df_valid['code']
        else:
            df_valid['product_name'] = df_valid['code']

        # กราฟแท่ง: สินค้าไหนออกเยอะสุด (By Qty)
        top_products = df_valid.groupby('product_name')['qty'].sum().sort_values(ascending=False).head(5)
        st.bar_chart(top_products, color="#FF4B4B") # สีแดง

    with col_chart2:
        st.subheader("💪 ผลงานทีมขาย (By Items Sold)")
        if 'sales_person' in df_valid.columns:
            # เปลี่ยนจากยอดเงิน เป็น "จำนวนชิ้น" ที่ขายได้
            sales_perf = df_valid.groupby('sales_person')['qty'].sum().sort_values(ascending=False)
            st.bar_chart(sales_perf, color="#29B5E8") # สีฟ้า
        else:
            st.info("ไม่พบคอลัมน์ sales_person")

    st.caption(f"Update: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
# 9. CANCEL ORDER (Fix: เลือกโชว์เฉพาะคอลัมน์ที่มีอยู่จริง กัน Error)
def render_cancel():
    st.header("🚫 Cancel Order (ยกเลิกรายการ)")
    st.info("ℹ️ ยกเลิกสถานะเป็น 'Cancelled' และคืนสต็อกอัตโนมัติ")
    
    df = get_data("Orders")
    if df.empty: st.info("ไม่มีข้อมูล"); return
    
    # 🟢 Clean ชื่อคอลัมน์
    df.columns = df.columns.str.strip()
    
    # กรองเฉพาะสถานะที่ยังยกเลิกได้
    active_status = ['Pending_Manager', 'Pending_SaleCO', 'Reserved']
    if 'status' not in df.columns:
        st.error("ไม่พบคอลัมน์ 'status' กรุณาตรวจสอบ Google Sheet")
        return

    mask = df['status'].isin(active_status)
    active_orders = df[mask]
    
    if active_orders.empty:
        st.success("✅ ไม่มีออเดอร์ค้างให้ยกเลิก")
        return
        
    all_ids = active_orders['id'].unique().tolist()
    sel_id = st.selectbox("เลือกเลขที่ออเดอร์", all_ids)
    
    if sel_id:
        items = active_orders[active_orders['id'] == sel_id]
        
        # กันเหนียว: เช็คชื่อคนขายกับลูกค้าก่อนดึง
        c_name = items.iloc[0]['customer_name'] if 'customer_name' in items.columns else "-"
        s_name = items.iloc[0]['sales_person'] if 'sales_person' in items.columns else "-"
        
        st.warning(f"⚠️ กำลังจะยกเลิก Order: {sel_id} | ลูกค้า: {c_name} | เซลล์: {s_name}")
        
        # 🟢 วิธีแก้จุดที่ Error: เลือกโชว์เฉพาะคอลัมน์ที่มีอยู่จริงเท่านั้น
        target_cols = ['code', 'qty', 'total', 'total_price', 'status'] # ใส่เผื่อไว้ทั้งคู่
        valid_cols = [c for c in target_cols if c in items.columns]
        
        st.dataframe(items[valid_cols], use_container_width=True)
        
        if st.button("🚨 ยืนยันการยกเลิก (Cancel Now)", type="primary"):
            run_query("update_order_status", oid=sel_id, status="Cancelled")
            st.success(f"✅ ยกเลิก Order {sel_id} เรียบร้อย!")
            time.sleep(2)
            st.rerun()

# ==========================================
# 🚀 MAIN APP LOGIC
# ==========================================
if check_password():
    role = st.session_state['user_role']
    user = st.session_state['user_name']
    
    with st.sidebar:
        # (ส่วนโลโก้...คงเดิม)
        if os.path.exists("images.png"):
            st.image("images.png", use_container_width=True)
            
        st.title(f"👤 {user}")
        st.caption(f"Role: {role}")
        st.divider()
        
        options = []
        
        # --- กำหนดสิทธิ์การมองเห็นเมนู ---
        if role == 'WH':
            options = ["WH Admin", "Support (ช่วยเหลือ)"]
        else:
            # เมนูพื้นฐานสำหรับ Sales/Admin/Manager
            if role in ['Admin', 'GM', 'CCO', 'Sale-CO', 'Sale']:
                options.append("1. Sale Report")
                options.append("2. Stock & Order")
                options.append("3. Catalogue (ดูสินค้า)")
            
            # เมนูอนุมัติ (Manager)
            if role in ['Admin', 'GM', 'CCO']:
                options.append("4. Manager Approve")
                options.append("8. Dashboard (ผู้บริหาร)") # 🟢 เพิ่ม Dashboard
            
            # เมนู Sale-CO
            if role in ['Admin', 'Sale-CO']:
                options.append("5. Sale-CO (Confirm Reserve)")
                options.append("9. Cancel Order (ยกเลิกบิล)") # 🟢 เพิ่ม Cancel ให้ Admin/Sale-CO
                
            # เมนู Admin
            if role == 'Admin':
                options.append("6. WH Admin")
            
            options.append("7. Support (ช่วยเหลือ)")

        if options:
            selected = st.radio("เมนูใช้งาน", options)
            st.divider()
            if st.button("Logout"): logout()
        else:
            st.error("Access Denied")
            if st.button("Logout"): logout()

    # Router (ตัวแยกทางเดิน)
    if "1." in selected: render_sale_report()
    elif "2." in selected: render_stock_order()
    elif "3." in selected: render_catalogue()
    elif "4." in selected: render_manager()
    elif "5." in selected: render_saleco()
    elif "6." in selected: render_wh()
    elif "WH Admin" in selected: render_wh()
    elif "Support" in selected: render_support()
    # 🟢 เพิ่มทางเดินใหม่
    elif "8." in selected: render_dashboard()
    elif "9." in selected: render_cancel()






























































