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

# 1. SALE REPORT (Version Final Stable: แก้ GPS Loop + จำค่าแม่นยำ)
def render_sale_report():
    st.header("📝 Sale Report & Visit Log")
    
    # --- 🟢 ส่วนจัดการ State (ความจำ) ---
    # เราต้องประกาศตัวแปรใน session_state ไว้ก่อน กันค่าหาย
    if 'edit_mode' not in st.session_state: st.session_state['edit_mode'] = False
    if 'edit_data' not in st.session_state: st.session_state['edit_data'] = {}
    
    # State สำหรับ GPS
    if 'gps_lat' not in st.session_state: st.session_state['gps_lat'] = None
    if 'gps_lon' not in st.session_state: st.session_state['gps_lon'] = None
    
    tab1, tab2 = st.tabs(["📸 บันทึกรายงานใหม่", "📂 ประวัติรายงาน"])
    
    with tab1:
        default_doc = generate_doc_no() if not st.session_state['edit_mode'] else st.session_state['edit_data']['doc_no']
        is_admin = st.session_state['user_role'] == 'Admin'
        default_name = st.session_state['user_name']
        
        st.info(f"📄 เลขที่เอกสาร: {default_doc}")
        
        # ชื่อเซลล์
        sales_name = st.text_input("ชื่อเซลล์", value=default_name, disabled=not is_admin)

        # =========================================================
        # 🟢 1. จัดการลูกค้า (Customer)
        # =========================================================
        df_cust = get_data("Customers")
        cust_name = "" 
        
        # --- ส่วนเพิ่มลูกค้าใหม่ ---
        with st.expander("➕ เพิ่มลูกค้าใหม่ (New Customer)", expanded=False):
            with st.form("add_new_cust_form"):
                c_new1, c_new2 = st.columns(2)
                new_name = c_new1.text_input("ชื่อลูกค้าใหม่")
                new_region = c_new2.selectbox("ภูมิภาค", ["กรุงเทพฯและปริมณฑล", "ภาคกลาง", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคตะวันออก", "ภาคตะวันตก", "ภาคใต้"])
                
                prov_list = sorted(df_cust['Province'].unique().tolist()) if not df_cust.empty else []
                new_prov = st.selectbox("จังหวัด", prov_list + ["ระบุเอง"])
                custom_prov = ""
                if new_prov == "ระบุเอง":
                    custom_prov = st.text_input("พิมพ์ชื่อจังหวัดเอง")
                
                if st.form_submit_button("💾 บันทึก"):
                    real_prov = custom_prov if new_prov == "ระบุเอง" else new_prov
                    if new_name and real_prov:
                         append_data("Customers", [new_name.strip(), real_prov, new_region])
                         st.success("✅ เพิ่มสำเร็จ!"); time.sleep(1); st.rerun()
                    else: st.error("กรอกข้อมูลให้ครบ")

        # --- ส่วนค้นหาลูกค้า (ระบบจำค่า) ---
        st.markdown("### 🏢 ข้อมูลลูกค้า")
        
        if not df_cust.empty:
            # ใช้ st.session_state เพื่อจำค่า Filter
            col_f1, col_f2, col_select = st.columns([1, 1, 2])
            
            # Filter 1: ภูมิภาค
            regions = ["- ทั้งหมด -"] + sorted(df_cust['Region'].dropna().unique().tolist())
            sel_region = col_f1.selectbox("1. ภูมิภาค", regions, key="filter_reg")
            
            # Filter Data
            df_step1 = df_cust
            if sel_region != "- ทั้งหมด -":
                df_step1 = df_step1[df_step1['Region'] == sel_region]
            
            # Filter 2: จังหวัด
            provinces = ["- ทั้งหมด -"] + sorted(df_step1['Province'].dropna().unique().tolist())
            sel_prov = col_f2.selectbox("2. จังหวัด", provinces, key="filter_prov")
            
            # Filter Data
            df_step2 = df_step1
            if sel_prov != "- ทั้งหมด -":
                df_step2 = df_step2[df_step2['Province'] == sel_prov]
            
            # Select 3: ชื่อลูกค้า
            customers = sorted(df_step2['Customer'].dropna().unique().tolist())
            
            # Logic: ถ้ากำลังแก้ไข ให้ดึงชื่อเดิมมาเป็น default index
            idx_cust = 0
            if st.session_state['edit_mode']:
                old_cust = st.session_state['edit_data'].get('customer_name', "")
                if old_cust in customers: idx_cust = customers.index(old_cust)
            
            # 🔴 จุดสำคัญ: ใส่ key เพื่อให้มันจำค่าได้
            sel_customer = col_select.selectbox("3. ชื่อลูกค้า", customers, index=idx_cust, key="select_cust_final")
            cust_name = sel_customer
            
            # แสดง Info
            if sel_customer:
                match = df_cust[df_cust['Customer'] == sel_customer]
                if not match.empty:
                    st.caption(f"📍 {match.iloc[0]['Province']} | {match.iloc[0]['Region']}")
        else:
            cust_name = st.text_input("ชื่อลูกค้า", key="manual_cust_input")

        # =========================================================
        # 🟢 2. GPS (แก้บั๊ก Loop นรก)
        # =========================================================
        st.write("---")
        col_gps1, col_gps2 = st.columns([1,3])
        with col_gps1: st.write("📍 **Location**")
        
        # 🔥 HERO FIX: ถ้ามีค่าแล้ว ไม่ต้องเรียก get_geolocation ซ้ำ!
        if st.session_state['gps_lat'] is None:
            loc = get_geolocation(component_key='gps_fix')
            if loc and 'coords' in loc:
                st.session_state['gps_lat'] = loc['coords']['latitude']
                st.session_state['gps_lon'] = loc['coords']['longitude']
                st.rerun() # รีโหลด 1 ทีเพื่อโชว์ค่า แล้วจบเลย
        
        with col_gps2:
            if st.session_state['gps_lat']:
                st.success(f"✅ GPS: {st.session_state['gps_lat']}, {st.session_state['gps_lon']}")
            else:
                st.warning("กำลังจับสัญญาณ... (ถ้าไม่ขึ้นให้กด Refresh 1 ที)")

        # =========================================================
        # 🟢 3. ข้อมูลคู่แข่ง (ต้องใส่ Key ให้จำค่า)
        # =========================================================
        st.write("---")
        st.write("🕵️ **ข้อมูลคู่แข่ง / ราคาตลาด**")
        
        df_comp = get_data("Competitor_Data")
        brands = ["- ไม่ระบุ -"]
        if not df_comp.empty: brands += sorted(df_comp['brand'].unique().tolist())
        brands.append("➕ เพิ่มยี่ห้อใหม่...")
        
        c_comp1, c_comp2 = st.columns(2)
        
        # Brand
        sel_brand = c_comp1.selectbox("ยี่ห้อ (Brand)", brands, key="sel_brand_stable")
        final_brand = sel_brand
        if sel_brand == "➕ เพิ่มยี่ห้อใหม่...":
            final_brand = c_comp1.text_input("ระบุยี่ห้อใหม่", key="new_brand_txt")
            
        # Product (Filter ตาม Brand)
        products = ["- ไม่ระบุ -"]
        if final_brand not in ["- ไม่ระบุ -", "➕ เพิ่มยี่ห้อใหม่..."] and not df_comp.empty:
             sub_df = df_comp[df_comp['brand'] == final_brand]
             products += sorted(sub_df['product'].unique().tolist())
        products.append("➕ เพิ่มสินค้าใหม่...")
        
        sel_prod = c_comp2.selectbox("รุ่น/สินค้า", products, key="sel_prod_stable")
        final_prod = sel_prod
        if sel_prod == "➕ เพิ่มสินค้าใหม่...":
            final_prod = c_comp2.text_input("ระบุสินค้าใหม่", key="new_prod_txt")

        # =========================================================
        # 🛡️ 4. THE IRON FORM (ฟอร์มป้องกันข้อมูลหาย)
        # =========================================================
        with st.form("main_entry_form"):
            st.info("👇 กรอกข้อมูลด้านล่างนี้ (ข้อมูลจะปลอดภัย ไม่หายเมื่อเว็บรีโหลด)")
            
            # ย้ายราคามาในนี้
            price = st.number_input("ราคาคู่แข่ง (บาท)", min_value=0.0, step=1.0)
            
            # เวลา
            now_thai = datetime.datetime.now() + datetime.timedelta(hours=7)
            d_visit = st.date_input("วันที่", now_thai.date())
            t_in = st.time_input("เวลาเข้า", now_thai.time())
            t_out = st.time_input("เวลาออก", now_thai.time())
            
            objs = st.multiselect("วัตถุประสงค์", ["1.เยี่ยมลูกค้า", "2.เสนอขาย", "3.เก็บเช็ค", "4.แก้ปัญหา", "5.อื่นๆ"])
            
            # ปัญหา & หมายเหตุ (ตัวที่ชอบหายที่สุด)
            # ดึงค่าเดิมถ้ามี
            old_prob = st.session_state['edit_data'].get('problem', "") if st.session_state['edit_mode'] else ""
            old_rem = st.session_state['edit_data'].get('remark', "") if st.session_state['edit_mode'] else ""
            
            prob = st.text_area("ปัญหา/Feedback", value=old_prob, height=100)
            rem = st.text_input("หมายเหตุ", value=old_rem)
            
            # รูปภาพ
            img_src = st.radio("รูปภาพ", ["🚫 ไม่แนบ", "📸 กล้อง", "📂 อัปโหลด"], horizontal=True)
            f_img = None
            if img_src == "📸 กล้อง": f_img = st.camera_input("ถ่ายรูป")
            elif img_src == "📂 อัปโหลด": f_img = st.file_uploader("เลือกไฟล์")

            st.write("---")
            btn_save = st.form_submit_button("💾 บันทึกรายงาน", type="primary", use_container_width=True)
            
            if btn_save:
                if cust_name:
                    # Save Logic
                    if final_brand and final_prod and final_brand not in ["- ไม่ระบุ -"] and final_prod not in ["- ไม่ระบุ -"]:
                         # Check duplicate competitor data
                         exists = False
                         if not df_comp.empty:
                             match = df_comp[(df_comp['brand']==final_brand) & (df_comp['product']==final_prod)]
                             if not match.empty: exists = True
                         if not exists: append_data("Competitor_Data", [final_brand, final_prod])
                    
                    link = ""
                    if f_img:
                        with st.spinner("Uploading..."): link = upload_image_to_imgbb(f_img)
                    
                    ts = str(datetime.datetime.now() + datetime.timedelta(hours=7))
                    row = [
                        default_doc, str(d_visit), sales_name, cust_name,
                        ", ".join(objs), prob, rem, link, 0, ts,
                        str(t_in), str(t_out), final_brand, final_prod, price,
                        str(st.session_state['gps_lat']), str(st.session_state['gps_lon'])
                    ]
                    
                    if st.session_state['edit_mode']:
                        cnt = int(st.session_state['edit_data'].get('edit_count', 0)) + 1
                        run_query("update_sale_report", doc_no=default_doc, cust=cust_name, obj=", ".join(objs), prob=prob, rem=rem, edit_count=cnt)
                        st.success("✅ แก้ไขเรียบร้อย")
                        st.session_state['edit_mode'] = False
                        st.session_state['edit_data'] = {}
                    else:
                        append_data("Sale_Reports", row)
                        st.success(f"✅ บันทึก: {default_doc}")
                        # Clear form state by rerun
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ ลืมเลือกลูกค้าครับ!")

    # Tab 2 History (เหมือนเดิม)
    with tab2:
        df = get_data("Sale_Reports")
        if not df.empty:
            df = df.iloc[::-1] # กลับด้าน
            for i, r in df.iterrows():
                with st.expander(f"{r['doc_no']} - {r['customer_name']}"):
                    st.write(r['problem'])
                    if st.button("แก้ไข", key=f"btn_edit_{r['doc_no']}"):
                        st.session_state['edit_mode'] = True
                        st.session_state['edit_data'] = r.to_dict()
                        st.rerun()
                         
# 2. STOCK & ORDER (ฉบับแก้ไข: ดูประวัติได้ตามสิทธิ์)
def render_stock_order():
    st.header("🛒 Check Stock & Open Order (ระบบตะกร้า)")
    
    if 'cart' not in st.session_state:
        st.session_state['cart'] = []
    
    # 🟢 1. ดึง Inventory
    df = get_data("Inventory")
    if df.empty:
        st.warning("⚠️ โหลดข้อมูล Stock ไม่สำเร็จ (ระบบอาจกำลังบันทึกข้อมูล)")
        if st.button("🔄 กดตรงนี้เพื่อโหลดใหม่ (Refresh)", type="primary"):
            st.rerun()
        return
    
    # 🟢 2. ดึง Orders (ต้องดึงตรงนี้ก่อน ถึงจะใช้ df_ord ได้)
    df_ord = get_data("Orders")
    if not df_ord.empty:
        df_ord.columns = df_ord.columns.str.strip()
        if 'customer_name' not in df_ord.columns and 'customer' in df_ord.columns:
            df_ord.rename(columns={'customer': 'customer_name'}, inplace=True)

    # ... (ส่วนคำนวณ Reserved เหมือนเดิม) ...
    reserved = pd.DataFrame()
    if not df_ord.empty:
        active_status = ['Pending_Manager', 'Pending_SaleCO', 'Reserved']
        if 'status' in df_ord.columns:
            pending = df_ord[df_ord['status'].isin(active_status)]
            if not pending.empty:
                reserved = pending.groupby('code')['qty'].sum().reset_index()
                reserved.columns = ['code', 'reserved_qty']
    
    df['code'] = df['code'].astype(str)
    if not reserved.empty:
        reserved['code'] = reserved['code'].astype(str)
        df = pd.merge(df, reserved, on='code', how='left')
    else:
        df['reserved_qty'] = 0
    df['reserved_qty'] = df['reserved_qty'].fillna(0)
    df['available'] = df['real_stock'] - df['reserved_qty']

    # --- ส่วนค้นหาและแสดงผล (เพิ่มตัวกรองหมวดหมู่) ---
    if 'category' in df.columns:
        all_cats = df['category'].dropna().unique().tolist()
        if all_cats:
            with st.expander("📂 ตัวกรองหมวดหมู่ (Filter Category)"):
                selected_cats = st.multiselect("เลือกประเภท/สี:", all_cats)
                if selected_cats:
                    df = df[df['category'].isin(selected_cats)]

    search = st.text_input("🔍 ค้นหาสินค้า")
    if search:
        mask = df['name'].astype(str).str.contains(search, case=False) | df['code'].astype(str).str.contains(search, case=False)
        df = df[mask]

    event = st.dataframe(
        df[['code', 'name', 'real_stock', 'reserved_qty', 'available', 'unit']], 
        column_config={"real_stock": "Stock", "reserved_qty": "Jong", "available": "Ready", "unit": "หน่วยนับ"},
        use_container_width=True, on_select="rerun", selection_mode="single-row"
    )

    if event.selection.rows:
        item = df.iloc[event.selection.rows[0]]
        st.divider()
        st.subheader(f"➕ เพิ่มลงตะกร้า: {item['name']}")
        c1, c2 = st.columns(2)
        qty = c1.number_input(f"จำนวน ({item['unit']})", min_value=1, value=1)
        ptype = c2.radio("ราคา", ["Normal", "Special"])
        price = 0.0
        if ptype == "Special":
            price = st.number_input("ระบุราคาพิเศษ", min_value=0.0)
            st.warning("⚠️ ราคาพิเศษต้องรออนุมัติ")

        if st.button("🛒 ใส่ตะกร้า", type="primary"):
            cart_item = {"code": item['code'], "name": item['name'], "qty": qty, "unit": item['unit'], "price": price, "type": ptype, "total": qty * price if ptype == "Special" else 0}
            st.session_state['cart'].append(cart_item)
            st.success(f"เพิ่ม {item['name']} จำนวน {qty} ลงตะกร้าแล้ว!")
            time.sleep(0.5)
            st.rerun()

    st.divider()
    st.subheader(f"🛒 ตะกร้าสินค้า ({len(st.session_state['cart'])})")
    if st.session_state['cart']:
        cart_df = pd.DataFrame(st.session_state['cart'])
        st.dataframe(cart_df, use_container_width=True)
        if st.button("❌ ล้างตะกร้า"):
            st.session_state['cart'] = []
            st.rerun()
        st.write("---")
        st.write("🚀 **ยืนยันการสั่งซื้อ**")
        c1, c2 = st.columns(2)
        s_name = c1.text_input("ชื่อเซลล์", value=st.session_state['user_name'], disabled=True)
        c_name = c2.text_input("ชื่อลูกค้า (Customer)")
        if st.button("✅ ยืนยันออเดอร์ (Confirm Order)", type="primary"):
            if c_name:
                so_id = generate_so_no()
                has_special = False
                # ... (ส่วนส่งเมลเดิม) ...
                for item in st.session_state['cart']:
                    status = "Pending_Manager" if item['type'] == "Special" else "Pending_SaleCO"
                    if item['type'] == "Special": has_special = True
                    row = [so_id, str(datetime.date.today()), s_name, c_name, item['code'], item['qty'], item['price'], item['total'], item['type'], status]
                    append_data("Orders", row)
                
                st.success(f"🎉 เปิดบิลสำเร็จ! เลขที่: {so_id}")
                st.session_state['cart'] = []
                time.sleep(2) 
                st.rerun()
            else: st.error("กรุณาระบุชื่อลูกค้า")
    else: st.info("ตะกร้ายังว่างอยู่ เลือกสินค้าด้านบนได้เลย")

    st.write("---")
    
    # 🟢🟢🟢 ส่วนประวัติการเปิดบิล (แก้ไขแล้ว) 🟢🟢🟢
    # เช็คก่อนว่ามี df_ord ไหม (กันเหนียว)
    if 'df_ord' in locals() and not df_ord.empty:
        user_role = st.session_state['user_role']
        my_name = st.session_state['user_name']

        # 1. เช็คสิทธิ์: ใครดูทั้งหมดได้บ้าง?
        if user_role in ['Admin', 'GM', 'CCO', 'Sale-CO']:
            history_df = df_ord.copy()
            history_title = "📜 ประวัติการเปิดบิลทั้งหมด (All Sale History)"
        else:
            # 2. นอกนั้นดูแค่ของตัวเอง
            if 'sales_person' in df_ord.columns:
                history_df = df_ord[df_ord['sales_person'] == my_name]
            else:
                history_df = pd.DataFrame() # กัน error
            history_title = "📜 ประวัติการเปิดบิลของฉัน (My Sale History)"

        # แจ้งเตือนรายการ Rejected (เตือนเฉพาะเจ้าของ)
        if not df_ord.empty and 'sales_person' in df_ord.columns:
            my_own_history = df_ord[df_ord['sales_person'] == my_name]
            if 'status' in my_own_history.columns:
                rejected_items = my_own_history[my_own_history['status'] == 'Rejected']
                if not rejected_items.empty:
                    st.error(f"❌ คุณมี {len(rejected_items)} รายการที่ 'ไม่อนุมัติ' (Rejected) กรุณาตรวจสอบ")

        # แสดงตาราง
        with st.expander(history_title, expanded=True):
            if not history_df.empty:
                history_df = history_df.iloc[::-1] # กลับด้าน (ล่าสุดขึ้นก่อน)
                
                # เพิ่ม sales_person ให้ผู้บริหารเห็น
                cols_to_show = ['id', 'date', 'sales_person', 'customer_name', 'code', 'qty', 'status']
                valid_cols = [c for c in cols_to_show if c in history_df.columns]
                
                def highlight_status(val):
                    color = 'black'
                    if val == 'Rejected': color = 'red'
                    elif val == 'Completed': color = 'green'
                    elif val == 'Reserved': color = 'blue'
                    elif val == 'Pending_Manager': color = 'orange'
                    elif val == 'Cancelled': color = 'gray'
                    return f'color: {color}'

                try:
                    st.dataframe(
                        history_df[valid_cols].style.applymap(highlight_status, subset=['status']), 
                        use_container_width=True,
                        hide_index=True
                    )
                except:
                    st.dataframe(history_df[valid_cols], use_container_width=True)
            else:
                st.caption("ยังไม่มีประวัติรายการ")
    else:
        st.info("ยังไม่มีข้อมูลออเดอร์ในระบบ")

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

# 5. WH ADMIN (Update: เพิ่ม Dashboard สรุปยอดรับ-จ่าย)
def render_wh():
    st.header("🏭 Warehouse Management")
    
    # เพิ่มแท็บ Dashboard ไว้หน้าสุด
    tab_dash, tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard (ภาพรวม)", "📦 Ship Orders (ตัดสต็อก)", "✏️ Adjust Stock", "📂 Upload Excel", "📜 History"])
    
    # --- TAB NEW: Dashboard ---
    with tab_dash:
        st.subheader("📈 สรุปความเคลื่อนไหวคลังสินค้า")
        
        # 1. ดึงข้อมูล Stock ปัจจุบัน
        df_inv = get_data("Inventory")
        
        # 2. ดึงข้อมูล Log การเคลื่อนไหว (WH_Logs)
        df_log = get_data("WH_Logs")
        
        # เตรียมตัวแปรสำหรับ KPI
        total_stock_now = 0
        inbound_month = 0
        outbound_month = 0
        
        # คำนวณ Stock ปัจจุบัน
        if not df_inv.empty:
            # แปลงเป็นตัวเลขกันเหนียว
            df_inv['real_stock'] = pd.to_numeric(df_inv['real_stock'], errors='coerce').fillna(0)
            total_stock_now = df_inv['real_stock'].sum()
        
        # คำนวณยอดรับเข้า/จ่ายออก เดือนนี้
        if not df_log.empty:
            # แปลงวันที่ให้เป็น datetime
            df_log['Date'] = pd.to_datetime(df_log['Date'], errors='coerce')
            df_log['Qty'] = pd.to_numeric(df_log['Qty'], errors='coerce').fillna(0)
            
            # กรองเฉพาะเดือนปัจจุบัน
            today = datetime.date.today()
            this_month_logs = df_log[
                (df_log['Date'].dt.month == today.month) & 
                (df_log['Date'].dt.year == today.year)
            ]
            
            if not this_month_logs.empty:
                # รับเข้า (Stock In)
                inbound_month = this_month_logs[this_month_logs['Action'] == 'Stock In']['Qty'].sum()
                
                # จ่ายออก (Stock Out + Ship Order)
                out_actions = ['Stock Out', 'Ship Order']
                outbound_month = this_month_logs[this_month_logs['Action'].isin(out_actions)]['Qty'].sum()

        # --- แสดง KPI Cards ---
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 สต็อกคงเหลือ (รวมทุกรุ่น)", f"{total_stock_now:,.0f} ม้วน")
        c2.metric("📥 รับเข้า (เดือนนี้)", f"{inbound_month:,.0f} ม้วน", delta="Stock In")
        c3.metric("📤 จ่ายออก/ขาย (เดือนนี้)", f"{outbound_month:,.0f} ม้วน", delta="-Stock Out", delta_color="inverse")
        
        st.divider()
        
        # --- แสดงกราฟ Top 5 ---
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("📥 Top 5 สินค้ารับเข้าเยอะสุด")
            if not df_log.empty and not this_month_logs.empty:
                df_in = this_month_logs[this_month_logs['Action'] == 'Stock In']
                if not df_in.empty:
                    top_in = df_in.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(5)
                    st.bar_chart(top_in, color="#2ecc71") # สีเขียว
                else:
                    st.info("เดือนนี้ยังไม่มีการรับของเข้า")
            else:
                st.info("ไม่มีข้อมูล")

        with col_g2:
            st.subheader("📤 Top 5 สินค้าเบิกออกเยอะสุด")
            if not df_log.empty and not this_month_logs.empty:
                # รวมทั้งเบิกใช้เอง และ ตัดขาย
                df_out = this_month_logs[this_month_logs['Action'].isin(['Stock Out', 'Ship Order'])]
                if not df_out.empty:
                    top_out = df_out.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(5)
                    st.bar_chart(top_out, color="#e74c3c") # สีแดง
                else:
                    st.info("เดือนนี้ยังไม่มีการเบิกของออก")
            else:
                st.info("ไม่มีข้อมูล")
    
    # --- TAB 1: Ship Orders (เหมือนเดิม) ---
    with tab1:
        st.subheader("🚚 รายการรอส่งของ (Reserved -> Ship)")
        st.info("ℹ️ รายการเหล่านี้ Sale-CO จองไว้แล้ว กดตัดสต็อกได้เลย")
        
        df_ord = get_data("Orders")
        if df_ord.empty: st.write("ไม่มีข้อมูล"); return
        
        # Clean columns
        df_ord.columns = df_ord.columns.str.strip()
        
        if 'status' in df_ord.columns:
            reserved_orders = df_ord[df_ord['status'] == 'Reserved']
            
            if reserved_orders.empty:
                st.success("✅ ไม่มีรายการรอส่งของ")
            else:
                order_groups = reserved_orders.groupby('id')
                for oid, items in order_groups:
                    cust_name = items.iloc[0]['customer_name'] if 'customer_name' in items.columns else "-"
                    with st.expander(f"📦 Order: {oid} | ลูกค้า: {cust_name}"):
                        st.dataframe(items[['code', 'qty', 'status']])
                        
                        if st.button("🚚 ตัดสต็อก & ส่งของ (Ship)", key=f"ship_{oid}"):
                            inv = get_data("Inventory")
                            # Clean columns inv
                            inv.columns = inv.columns.str.strip()
                            
                            for _, item in items.iterrows():
                                # หา Stock เก่า
                                match_row = inv.loc[inv['code'].astype(str) == str(item['code'])]
                                if not match_row.empty:
                                    curr_stock = match_row['real_stock'].values[0]
                                    # คำนวณ Stock ใหม่
                                    new_stock = int(curr_stock) - int(item['qty'])
                                    # อัปเดต Google Sheet
                                    run_query("update_stock", code=str(item['code']), new_stock=new_stock)
                                    
                                    # บันทึก Log
                                    ts = str(datetime.datetime.now())
                                    today = str(datetime.date.today())
                                    item_name_log = match_row['name'].values[0] if 'name' in match_row else str(item['code'])
                                    unit_log = match_row['unit'].values[0] if 'unit' in match_row else "-"
                                    
                                    log_row = [ts, today, "Ship Order", str(item['code']), item_name_log, item['qty'], unit_log, st.session_state['user_name']]
                                    append_data("WH_Logs", log_row)
                            
                            # อัปเดตสถานะบิลเป็น Completed
                            run_query("update_order_status", oid=oid, status="Completed")
                            st.success(f"✅ ตัดสต็อก Order {oid} เรียบร้อย!")
                            time.sleep(1)
                            st.rerun()
        else:
            st.error("ไม่พบคอลัมน์ status ใน Orders")

    # --- TAB 2: Adjust Stock (เหมือนเดิม) ---
    with tab2:
        df = get_data("Inventory")
        if not df.empty:
            search = st.text_input("ค้นหา:", placeholder="Code/Name")
            if search: 
                mask = df['code'].astype(str).str.contains(search, case=False) | df['name'].astype(str).str.contains(search, case=False)
                df = df[mask]
            
            if 'remark' not in df.columns: df['remark'] = ""
            
            event = st.dataframe(
                df[['code','name','real_stock','unit', 'remark']], 
                column_config={"unit": "หน่วยนับ", "remark": "หมายเหตุล่าสุด"}, 
                on_select="rerun", selection_mode="single-row", use_container_width=True
            )
            
            if event.selection.rows:
                item = df.iloc[event.selection.rows[0]]
                st.write("---")
                st.info(f"สินค้า: {item['name']} | 📦 ของเดิม: {item['real_stock']} {item['unit']}")
                
                # โซนจัดการหมายเหตุ
                c_rem1, c_rem2 = st.columns([3, 1])
                remark_val = c_rem1.text_input("📝 แก้ไขหมายเหตุ (Internal Note)", value=str(item['remark']))
                if c_rem2.button("💾 บันทึกหมายเหตุ", use_container_width=True):
                    run_query("update_stock", code=str(item['code']), remark=remark_val)
                    st.success("✅ อัปเดตหมายเหตุเรียบร้อย!")
                    time.sleep(1)
                    st.rerun()
                
                st.write("---")
                
                # โซนจัดการสต็อก
                adjust_label = f"ระบุจำนวนสินค้า ({item['unit']})"
                adjust_qty = st.number_input(adjust_label, min_value=0, step=1, value=0)
                
                c1, c2 = st.columns(2)
                
                # ปุ่มเพิ่ม
                if c1.button("➕ เพิ่ม Stock (รับเข้า)", use_container_width=True, type="primary"):
                    if adjust_qty > 0:
                        new_val = int(item['real_stock']) + adjust_qty
                        run_query("update_stock", code=str(item['code']), new_stock=new_val)
                        
                        ts = str(datetime.datetime.now())
                        today = str(datetime.date.today())
                        log_row = [ts, today, "Stock In", str(item['code']), item['name'], adjust_qty, item['unit'], st.session_state['user_name']]
                        append_data("WH_Logs", log_row)
                        
                        st.success(f"✅ รับเข้า {adjust_qty} เรียบร้อย! (ยอดใหม่: {new_val})")
                        time.sleep(1)
                        st.rerun()
                    else: st.warning("ระบุจำนวน > 0")

                # ปุ่มลด
                if c2.button("➖ ตัด Stock (จ่ายออก)", use_container_width=True):
                    if adjust_qty > 0:
                        new_val = int(item['real_stock']) - adjust_qty
                        run_query("update_stock", code=str(item['code']), new_stock=new_val)
                        
                        ts = str(datetime.datetime.now())
                        today = str(datetime.date.today())
                        log_row = [ts, today, "Stock Out", str(item['code']), item['name'], adjust_qty, item['unit'], st.session_state['user_name']]
                        append_data("WH_Logs", log_row)
                        
                        st.warning(f"🔻 จ่ายออก {adjust_qty} เรียบร้อย! (ยอดใหม่: {new_val})")
                        time.sleep(1)
                        st.rerun()
                    else: st.warning("ระบุจำนวน > 0")

    # --- TAB 3: Upload Excel (เหมือนเดิม) ---
    with tab3:
        st.warning("⚠️ การ Upload Excel จะลบข้อมูลเดิมทั้งหมด")
        up = st.file_uploader("เลือกไฟล์ Excel Stock (.xlsx)", type=['xlsx'])
        if up and st.button("🚀 เริ่มอัปโหลด"):
            try:
                df_new = pd.read_excel(up)
                df_new.columns = df_new.columns.str.strip()
                df_new['Stock'] = pd.to_numeric(df_new['Stock'], errors='coerce').fillna(0)
                df_new = df_new.fillna("")
                upload_data = []
                for _, r in df_new.iterrows():
                    row = [str(r['code']), str(r['กลุ่ม']), str(r['รายละเอียด']), int(r['Stock']), str(r['หน่วยนับขนาน']), ""]
                    upload_data.append(row)
                client = get_gsheet_client()
                wks = client.open(SHEET_NAME).worksheet("Inventory")
                wks.clear()
                wks.append_row(['code', 'category', 'name', 'real_stock', 'unit', 'remark'])
                wks.append_rows(upload_data)
                st.success(f"✅ อัปโหลดสำเร็จ {len(upload_data)} รายการ!")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    # --- TAB 4: History (เหมือนเดิม) ---
    with tab4:
        st.subheader("📜 ประวัติการ รับเข้า/จ่ายออก")
        sel_date = st.date_input("เลือกวันที่ดูประวัติ", datetime.date.today())
        df_log = get_data("WH_Logs")
        if not df_log.empty:
            df_log['Date'] = pd.to_datetime(df_log['Date'], errors='coerce').dt.date.astype(str)
            # แปลงเป็น String เพื่อเทียบกับ input
            daily_log = df_log[df_log['Date'] == str(sel_date)]
            if not daily_log.empty:
                daily_log = daily_log.sort_values(by='Timestamp', ascending=False)
                st.info(f"📅 รายการประจำวันที่: {sel_date}")
                st.dataframe(daily_log[['Timestamp', 'Action', 'Name', 'Qty', 'Unit', 'User']], hide_index=True, use_container_width=True)
            else:
                st.warning(f"🚫 ไม่พบรายการเคลื่อนไหวในวันที่ {sel_date}")
        else:
            st.warning("ยังไม่มีประวัติการใช้งาน")
            
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

































