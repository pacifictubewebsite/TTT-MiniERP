import streamlit as st
import pandas as pd
import datetime
import time
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
    "Jitpanu": {"pass": "Jitpanu@TTT2026", "role": "GM", "name": "Jitpanu"},
    "Theerapon": {"pass": "Theer@pon01", "role": "CCO", "name": "Theeraphol"},
    "chaiyakit": {"pass": "Chaiyakit2026", "role": "Sale-CO", "name": "Chaiyakit"},
    "nattapong": {"pass": "Nattapong2026", "role": "Sale", "name": "Nattapong"},
    "samanan": {"pass": "Samanan2026", "role": "Sale", "name": "Samanan"},
    "suksun": {"pass": "Suksun2026", "role": "Sale", "name": "Suksun"},
    "wutthipong": {"pass": "Wutthipong2026", "role": "Sale", "name": "Wutthipong"},
    "Podjana": {"pass": "Podjana@sale002", "role": "Sale", "name": "Pojana"},
    "siva": {"pass": "Siva2026", "role": "Sale", "name": "Siva"},
    "sale04": {"pass": "S@le04", "role": "Sale", "name": "Sale04"},
    "vichai": {"pass": "Vichai2026", "role": "WH", "name": "Vichai"}
}

# ==========================================
# ☁️ GOOGLE SHEETS CONNECTION
# ==========================================
@st.cache_resource
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

# 1. SALE REPORT (Update: GPS Check-in)
def render_sale_report():
    st.header("📝 Sale Report & Visit Log")
    if 'edit_mode' not in st.session_state:
        st.session_state['edit_mode'] = False
        st.session_state['edit_data'] = {}

    tab1, tab2 = st.tabs(["📸 บันทึกรายงานใหม่", "📂 ประวัติรายงาน"])
    
    with tab1:
        default_doc = generate_doc_no() if not st.session_state['edit_mode'] else st.session_state['edit_data']['doc_no']
        is_admin = st.session_state['user_role'] == 'Admin'
        default_name = st.session_state['user_name']
        st.info(f"📄 เลขที่เอกสาร: {default_doc}")
        
        c1, c2 = st.columns(2)
        sales_name = c1.text_input("ชื่อเซลล์", value=default_name, disabled=not is_admin)
        default_cust = st.session_state['edit_data'].get('customer_name', "") if st.session_state['edit_mode'] else ""
        cust_name = c2.text_input("ชื่อลูกค้า / บริษัท", value=default_cust)
        
        # --- 📍 GPS SECTION (Check-in) ---
        st.write("---")
        st.write("📍 **Check-in ตำแหน่งปัจจุบัน**")
        
        # ตัวแปรเก็บค่า GPS
        gps_lat = ""
        gps_lon = ""
        
        # เรียกใช้ฟังก์ชัน GPS (ถ้ากดปุ่ม มันจะดึงค่ามา)
        # หมายเหตุ: get_geolocation จะทำงานเมื่อหน้าเว็บโหลดหรือมีการกระตุ้น
        loc = get_geolocation(component_key='get_gps')
        
        if loc and 'coords' in loc:
            gps_lat = loc['coords']['latitude']
            gps_lon = loc['coords']['longitude']
            st.success(f"✅ จับสัญญาณ GPS สำเร็จ! ({gps_lat}, {gps_lon})")
        else:
            st.warning("⚠️ กำลังค้นหาตำแหน่ง... (กรุณากด 'Allow' ถ้าเบราว์เซอร์ถาม)")

        # แสดงค่าในช่องที่แก้ไขไม่ได้ (Disabled)
        g1, g2 = st.columns(2)
        g1.text_input("Latitude", value=gps_lat, disabled=True)
        g2.text_input("Longitude", value=gps_lon, disabled=True)
        
        st.caption("ℹ️ หากตำแหน่งไม่ขึ้น ให้รีเฟรชหน้าเว็บ หรือตรวจสอบการอนุญาต Location บนมือถือ")
        st.write("---")
        # -----------------------------------

        now = datetime.datetime.now().replace(second=0, microsecond=0)
        t1, t2, t3 = st.columns(3)
        date_visit = t1.date_input("วันที่", datetime.date.today())
        time_in = t2.time_input("เวลาเข้า (Check-in)", value=now.time(), step=60) 
        time_out = t3.time_input("เวลาออก (Check-out)", value=now.time(), step=60)

        obj_options = ["1.เข้าพบ/เยี่ยมลูกค้า", "2.เสนอขายสินค้า", "3.วางบิลเก็บเช็ค", "4.แก้ปัญหา", "5.อื่นๆ"]
        selected_objs = st.multiselect("วัตถุประสงค์", obj_options)
        
        # ข้อมูลคู่แข่ง (Cascading)
        st.write("---")
        st.write("🕵️ **ข้อมูลคู่แข่ง / ราคาตลาด**")
        
        df_comp = get_data("Competitor_Data")
        if not df_comp.empty:
            brand_options = sorted(df_comp['brand'].unique().tolist())
        else:
            brand_options = []
        brand_options.insert(0, "- ไม่ระบุ -")
        brand_options.append("➕ เพิ่มยี่ห้อใหม่...")
        
        col_comp1, col_comp2, col_comp3 = st.columns(3)
        selected_brand = col_comp1.selectbox("ยี่ห้อสินค้า (Brand)", brand_options, key="sel_brand_key")
        final_brand = ""
        if selected_brand == "➕ เพิ่มยี่ห้อใหม่...":
            final_brand = col_comp1.text_input("ระบุยี่ห้อใหม่", placeholder="เช่น ท่อไทยใจดี", key="txt_brand_new")
        elif selected_brand != "- ไม่ระบุ -":
            final_brand = selected_brand

        product_options = []
        if final_brand and final_brand not in ["➕ เพิ่มยี่ห้อใหม่...", "- ไม่ระบุ -"]:
            if not df_comp.empty and 'product' in df_comp.columns:
                filtered_df = df_comp[df_comp['brand'] == final_brand]
                product_options = sorted(filtered_df['product'].unique().tolist())
        product_options.insert(0, "- ไม่ระบุ -")
        product_options.append("➕ เพิ่มสินค้าใหม่...")
        
        selected_prod = col_comp2.selectbox("รุ่น/สินค้า (Product)", product_options, key="sel_prod_key")
        final_prod = ""
        if selected_prod == "➕ เพิ่มสินค้าใหม่...":
            final_prod = col_comp2.text_input("ระบุสินค้าใหม่", placeholder="เช่น ท่อ 4 นิ้ว", key="txt_prod_new")
        elif selected_prod != "- ไม่ระบุ -":
            final_prod = selected_prod

        comp_price = col_comp3.number_input("ราคาที่ลูกค้าซื้อเข้า", min_value=0.0, step=0.1, key="num_price_key")
        st.write("---")
        
        default_prob = st.session_state['edit_data'].get('problem', "") if st.session_state['edit_mode'] else ""
        problem = st.text_area("ปัญหา/Feedback", value=default_prob)
        default_rem = st.session_state['edit_data'].get('remark', "") if st.session_state['edit_mode'] else ""
        remark = st.text_input("หมายเหตุ", value=default_rem)
        
        img_method = st.radio("เลือกวิธีแนบรูป:", ["🚫 ไม่แนบ", "📸 เปิดกล้อง (Camera)", "📂 อัปโหลดไฟล์ (Upload)"], horizontal=True)
        img_file = None
        if img_method == "📸 เปิดกล้อง (Camera)":
            img_file = st.camera_input("ถ่ายรูป")
        elif img_method == "📂 อัปโหลดไฟล์ (Upload)":
            img_file = st.file_uploader("เลือกรูปจากเครื่อง", type=['jpg', 'png', 'jpeg'])
        
        st.write("---")
        
        if st.session_state['edit_mode']:
            if st.button("💾 บันทึกการแก้ไข", type="primary"):
                current_edit_count = int(st.session_state['edit_data'].get('edit_count', 0)) + 1
                final_obj = ", ".join(selected_objs)
                # Note: Edit mode doesn't update GPS for simplicity
                run_query("update_sale_report", doc_no=default_doc, cust=cust_name, obj=final_obj, prob=problem, rem=remark, edit_count=current_edit_count)
                log_row = [default_doc, current_edit_count, st.session_state['user_name'], str(datetime.datetime.now()), f"Edit: {remark}"]
                append_data("Sale_Report_Logs", log_row)
                st.success("✅ แก้ไขเรียบร้อย!")
                st.session_state['edit_mode'] = False
                st.session_state['edit_data'] = {}
                time.sleep(1)
                st.rerun()
            if st.button("ยกเลิกการแก้ไข"):
                st.session_state['edit_mode'] = False
                st.session_state['edit_data'] = {}
                st.rerun()
        else:
            if st.button("💾 บันทึกรายงานใหม่", type="primary"):
                if cust_name:
                    if final_brand and final_prod:
                        is_exist = False
                        if not df_comp.empty:
                            match = df_comp[(df_comp['brand'] == final_brand) & (df_comp['product'] == final_prod)]
                            if not match.empty: is_exist = True
                        if not is_exist:
                            append_data("Competitor_Data", [final_brand, final_prod])

                    final_obj = ", ".join(selected_objs)
                    saved_link = "" 

                    if img_file:
                        # 👇 เปลี่ยนมาเรียกฟังก์ชัน ImgBB (ไม่ต้องส่งชื่อไฟล์ ส่งแค่รูปพอ)
                        with st.spinner("กำลังอัปโหลดรูป..."):
                            saved_link = upload_image_to_imgbb(img_file)
                    
                    # 🟢 บันทึกข้อมูล (เหมือนเดิม)
                    row = [
                        default_doc, 
                        # ...
                        saved_link, # เก็บลิงก์ ImgBB ลง Sheet
                        # ...
                    ]
                    
                    # 🟢 บันทึก GPS ลง Database (Lat, Lon)
                    row = [
                        default_doc, 
                        str(date_visit), 
                        sales_name, 
                        cust_name, 
                        final_obj, 
                        problem, 
                        remark, 
                        saved_link, # 👈 แก้ตรงนี้ครับ! (จาก saved_path เป็น saved_link)
                        0, 
                        str(datetime.datetime.now()),
                        time_in.strftime("%H:%M"), 
                        time_out.strftime("%H:%M"), 
                        final_brand, 
                        final_prod, 
                        comp_price,
                        str(gps_lat), 
                        str(gps_lon)
                    ]
                    
                    append_data("Sale_Reports", row)
                    
                    st.success(f"✅ บันทึกสำเร็จ: {default_doc}")
                    keys_to_clear = ["sel_brand_key", "txt_brand_new", "sel_prod_key", "txt_prod_new", "num_price_key"]
                    for k in keys_to_clear:
                        if k in st.session_state: del st.session_state[k]
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อลูกค้า")

    with tab2:
        df = get_data("Sale_Reports")
        if not df.empty:
            user_role = st.session_state['user_role']
            my_name = st.session_state['user_name']
            if user_role == "Sale":
                df = df[df['sales_person'] == my_name]
            df = df.sort_values(by='doc_no', ascending=False)
            
            for _, row in df.iterrows():
                edit_info = ""
                if row['edit_count'] > 0 and user_role in ['Admin', 'GM', 'CCO', 'Sale-CO']:
                    edit_info = f"🔴 (Edited {row['edit_count']} times)"
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    with st.expander(f"📄 {row['doc_no']} | {row['customer_name']} {edit_info}"):
                        st.write(f"**วันที่:** {row['date']}")
                        if 'time_in' in row and row['time_in']:
                            st.write(f"🕒 **เวลา:** {row['time_in']} - {row['time_out']}")
                        
                        # 🟢 โชว์พิกัด GPS (ถ้ามี)
                        if 'lat' in row and row['lat'] and row['lat'] != "":
                            st.info(f"📍 **Check-in:** {row['lat']}, {row['lon']}")
                            st.link_button("🗺️ ดูแผนที่ Google Maps", f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}")

                        st.write(f"**วัตถุประสงค์:** {row['objective']}")
                        if 'comp_name' in row and row['comp_name']:
                            st.write(f"🕵️ **คู่แข่ง:** {row['comp_name']} | {row['comp_product']} | {row['comp_price']}")
                        st.write(f"**ปัญหา:** {row['problem']}")
                        st.write(f"**หมายเหตุ:** {row['remark']}")
                        img_source = str(row['image_path']).strip()
                        
                        if img_source:
                            # 1. ถ้าเป็นลิงก์ (ขึ้นต้นด้วย http) -> โชว์เลย
                            if img_source.startswith("http"):
                                st.image(img_source, caption="รูปหน้างาน (Online)", use_container_width=True)
                            
                            # 2. ถ้าเป็นไฟล์ในเครื่อง (ของเก่า) -> เช็คก่อนว่ามีไฟล์ไหม
                            elif os.path.exists(img_source):
                                st.image(img_source, caption="รูปหน้างาน (Local)", use_container_width=True)
                with col_b:
                    if row['sales_person'] == my_name or user_role == 'Admin':
                        if st.button("✏️ แก้ไข", key=f"edit_{row['doc_no']}"):
                            st.session_state['edit_mode'] = True
                            st.session_state['edit_data'] = row.to_dict()
                            st.rerun()

# 2. STOCK & ORDER (Update: เพิ่มการแจ้งเตือนเมื่อโดน Reject ในหน้าประวัติ)
def render_stock_order():
    st.header("🛒 Check Stock & Open Order (ระบบตะกร้า)")
    
    if 'cart' not in st.session_state:
        st.session_state['cart'] = []
    
    # 🟢 1. ดึง Inventory (แบบ Retry)
    df = get_data("Inventory")
    if df.empty:
        st.warning("⚠️ โหลดข้อมูล Stock ไม่สำเร็จ (ระบบอาจกำลังบันทึกข้อมูล)")
        if st.button("🔄 กดตรงนี้เพื่อโหลดใหม่ (Refresh)", type="primary"):
            st.rerun()
        return
    
    # 🟢 2. ดึง Orders
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

    # --- ส่วนค้นหาและแสดงผล (เหมือนเดิม) ---
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
                items_html_list = ""
                for item in st.session_state['cart']:
                    status = "Pending_Manager" if item['type'] == "Special" else "Pending_SaleCO"
                    if item['type'] == "Special": has_special = True
                    price_txt = f"ราคาขออนุมัติ: {item['price']:,} บาท" if item['type'] == "Special" else "ราคา: ปกติ"
                    items_html_list += f"<li><b>สินค้า:</b> {item['name']} (Code: {item['code']}) <br> <b>จำนวน:</b> {item['qty']} {item['unit']} | {price_txt}</li>"
                    row = [so_id, str(datetime.date.today()), s_name, c_name, item['code'], item['qty'], item['price'], item['total'], item['type'], status]
                    append_data("Orders", row)
                try:
                    if has_special:
                        subject = f"🔥 ขออนุมัติราคาพิเศษ (Special Price Request) - {so_id}"
                        receivers = ["jitpanu@pacifictube.com", "theerapon@hosecenter.co.th"]
                        body = f"<p>เรียน GM/CCO,</p><p>มีรายการขอราคาพิเศษ: {so_id} จาก {s_name}</p><ul>{items_html_list}</ul><p>โปรดอนุมัติในระบบ TTT Mini ERP</p>"
                        send_email_notification(receivers, subject, body)
                    else:
                        subject = f"📦 แจ้งเตือนออเดอร์ใหม่ - {so_id}"
                        receivers = ["Chaiyakit@pacifictube.com"]
                        body = f"<p>เรียน Sale-CO,</p><p>มีออเดอร์ใหม่: {so_id} จาก {s_name}</p><ul>{items_html_list}</ul><p>โปรดตรวจสอบในระบบ</p>"
                        send_email_notification(receivers, subject, body)
                except: pass
                st.success(f"🎉 เปิดบิลสำเร็จ! เลขที่: {so_id}")
                st.session_state['cart'] = []
                time.sleep(2) 
                st.rerun()
            else: st.error("กรุณาระบุชื่อลูกค้า")
    else: st.info("ตะกร้ายังว่างอยู่ เลือกสินค้าด้านบนได้เลย")

    st.write("---")
    
    # 🟢🟢🟢 ส่วนที่เพิ่ม: แจ้งเตือนสถานะ Rejected 🟢🟢🟢
    if not df_ord.empty and 'sales_person' in df_ord.columns:
        my_history = df_ord[df_ord['sales_person'] == st.session_state['user_name']]
        
        # เช็คว่ามีรายการที่โดนปฏิเสธล่าสุดไหม
        if 'status' in my_history.columns:
            rejected_items = my_history[my_history['status'] == 'Rejected']
            if not rejected_items.empty:
                st.error(f"❌ คุณมี {len(rejected_items)} รายการที่ 'ไม่อนุมัติ' (Rejected) กรุณาตรวจสอบและติดต่อ Sale-CO")

        with st.expander("📜 ประวัติการเปิดบิลของฉัน (My Sale History)"):
            if not my_history.empty:
                my_history = my_history.iloc[::-1]
                cols_to_show = ['id', 'date', 'customer_name', 'code', 'qty', 'status']
                valid_cols = [c for c in cols_to_show if c in my_history.columns]
                
                # แสดงผลแบบ Highlight สีสถานะ
                def highlight_status(val):
                    color = 'black'
                    if val == 'Rejected': color = 'red'
                    elif val == 'Completed': color = 'green'
                    elif val == 'Reserved': color = 'blue'
                    elif val == 'Pending_Manager': color = 'orange'
                    return f'color: {color}'

                try:
                    st.dataframe(my_history[valid_cols].style.applymap(highlight_status, subset=['status']), use_container_width=True)
                except:
                    st.dataframe(my_history[valid_cols], use_container_width=True)
            else:
                st.caption("ยังไม่มีประวัติการขาย")

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
            if role in ['Admin', 'GM']:
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

















