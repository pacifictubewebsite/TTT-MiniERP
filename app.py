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
    "jitpanu": {"pass": "Jitpanu2026", "role": "GM", "name": "Jitpanu"},
    "theeraphol": {"pass": "Theeraphol2026", "role": "CCO", "name": "Theeraphol"},
    "chaiyakit": {"pass": "Chaiyakit2026", "role": "Sale-CO", "name": "Chaiyakit"},
    "nattapong": {"pass": "Nattapong2026", "role": "Sale", "name": "Nattapong"},
    "samanan": {"pass": "Samanan2026", "role": "Sale", "name": "Samanan"},
    "suksun": {"pass": "Suksun2026", "role": "Sale", "name": "Suksun"},
    "wutthipong": {"pass": "Wutthipong2026", "role": "Sale", "name": "Wutthipong"},
    "pojana": {"pass": "Pojana2026", "role": "Sale", "name": "Pojana"},
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
        try:
            sh = client.open(SHEET_NAME)
            wks = sh.worksheet(worksheet_name)
            data = wks.get_all_records()
            return pd.DataFrame(data)
        except: return pd.DataFrame()
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
        
        # 🟢 แยกการทำงาน: ถ้าส่ง Stock มาค่อยแก้ Stock
        if 'new_stock' in kwargs:
            wks.update_cell(cell.row, 4, kwargs['new_stock'])

        # 🟢 แยกการทำงาน: ถ้าส่ง Remark มาค่อยแก้ Remark
        if 'remark' in kwargs:
            wks.update_cell(cell.row, 6, kwargs['remark'])

    elif query_type == "update_order_status":
        wks = sh.worksheet("Orders")
        cell_list = wks.findall(str(kwargs['oid']))
        col_status = 10
        for cell in cell_list:
            wks.update_cell(cell.row, col_status, kwargs['status'])

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
                    saved_path = ""
                    if img_file:
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = f"IMG_{ts}.jpg"
                        saved_path = os.path.join(UPLOAD_FOLDER, fname)
                        with open(saved_path, "wb") as f: f.write(img_file.getbuffer())

                    # 🟢 บันทึก GPS ลง Database (Lat, Lon)
                    row = [
                        default_doc, str(date_visit), sales_name, cust_name, final_obj, 
                        problem, remark, saved_path, 0, str(datetime.datetime.now()),
                        time_in.strftime("%H:%M"), 
                        time_out.strftime("%H:%M"), 
                        final_brand, final_prod, comp_price,
                        str(gps_lat), str(gps_lon) # เพิ่ม 2 ช่องนี้
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
                        if row['image_path'] and os.path.exists(row['image_path']):
                            st.image(row['image_path'], caption="รูปหน้างาน")
                with col_b:
                    if row['sales_person'] == my_name or user_role == 'Admin':
                        if st.button("✏️ แก้ไข", key=f"edit_{row['doc_no']}"):
                            st.session_state['edit_mode'] = True
                            st.session_state['edit_data'] = row.to_dict()
                            st.rerun()

# 2. STOCK & ORDER (เหมือนเดิม)
def render_stock_order():
    st.header("🛒 Check Stock & Open Order (ระบบตะกร้า)")
    if 'cart' not in st.session_state: st.session_state['cart'] = []
    df = get_data("Inventory")
    if df.empty: st.warning("Stock Data Not Found"); return
    df_ord = get_data("Orders")
    if not df_ord.empty:
        df_ord.columns = df_ord.columns.str.strip()
        if 'customer_name' not in df_ord.columns and 'customer' in df_ord.columns:
            df_ord.rename(columns={'customer': 'customer_name'}, inplace=True)
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
    else: df['reserved_qty'] = 0
    df['reserved_qty'] = df['reserved_qty'].fillna(0)
    df['available'] = df['real_stock'] - df['reserved_qty']
    search = st.text_input("🔍 ค้นหาสินค้า")
    if search:
        mask = df['name'].astype(str).str.contains(search, case=False) | df['code'].astype(str).str.contains(search, case=False)
        df = df[mask]
    event = st.dataframe(df[['code', 'name', 'real_stock', 'reserved_qty', 'available', 'unit']], column_config={"real_stock": "Stock", "reserved_qty": "Jong", "available": "Ready", "unit": "หน่วยนับ"}, use_container_width=True, on_select="rerun", selection_mode="single-row")
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
                for item in st.session_state['cart']:
                    status = "Pending_Manager" if item['type'] == "Special" else "Pending_SaleCO"
                    row = [so_id, str(datetime.date.today()), s_name, c_name, item['code'], item['qty'], item['price'], item['total'], item['type'], status]
                    append_data("Orders", row)
                st.success(f"🎉 เปิดบิลสำเร็จ! เลขที่: {so_id}")
                st.session_state['cart'] = []
                time.sleep(2)
                st.rerun()
            else: st.error("กรุณาระบุชื่อลูกค้า")
    else: st.info("ตะกร้ายังว่างอยู่ เลือกสินค้าด้านบนได้เลย")
    st.write("---")
    with st.expander("📜 ประวัติการเปิดบิลของฉัน (My Sale History)"):
        if not df_ord.empty:
            if 'sales_person' in df_ord.columns:
                my_history = df_ord[df_ord['sales_person'] == st.session_state['user_name']]
                if not my_history.empty:
                    my_history = my_history.iloc[::-1]
                    cols_to_show = ['id', 'date', 'customer_name', 'code', 'qty', 'status']
                    valid_cols = [c for c in cols_to_show if c in my_history.columns]
                    st.dataframe(my_history[valid_cols], use_container_width=True)
                else: st.caption("ยังไม่มีประวัติการขาย")
            else: st.error("⚠️ ไม่พบคอลัมน์ 'sales_person' ใน Sheet Orders")

# 3. MANAGER APPROVE (เหมือนเดิม)
def render_manager():
    st.header("👔 Approval Dashboard")
    df = get_data("Orders")
    if df.empty: st.info("ไม่มีข้อมูล"); return
    pending = df[df['status'] == 'Pending_Manager']
    if pending.empty: st.success("✅ ไม่มีรายการค้างอนุมัติ"); return
    order_groups = pending.groupby('id')
    for oid, items in order_groups:
        with st.expander(f"Order: {oid} | เซลล์: {items.iloc[0]['sales_person']} | ลูกค้า: {items.iloc[0]['customer_name']}"):
            st.dataframe(items[['code', 'qty', 'unit_price', 'total_price']])
            c1, c2 = st.columns(2)
            if c1.button("อนุมัติทั้งบิล", key=f"app_{oid}"):
                run_query("update_order_status", oid=oid, status="Pending_SaleCO")
                st.success("Approved!")
                time.sleep(1)
                st.rerun()
            if c2.button("ไม่อนุมัติ", key=f"rej_{oid}"):
                run_query("update_order_status", oid=oid, status="Cancelled")
                st.error("Rejected!")
                time.sleep(1)
                st.rerun()

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

# 5. WH ADMIN (Update: แยกปุ่มหมายเหตุ ออกจากปุ่มสต็อก)
def render_wh():
    st.header("🏭 Warehouse Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Ship Orders (ตัดสต็อก)", "✏️ Adjust Stock", "📂 Upload Excel", "📜 History"])
    
    # --- TAB 1: Ship Orders (เหมือนเดิม) ---
    with tab1:
        st.subheader("🚚 รายการรอส่งของ (Reserved -> Ship)")
        st.info("ℹ️ รายการเหล่านี้ Sale-CO จองไว้แล้ว กดตัดสต็อกได้เลย")
        
        df_ord = get_data("Orders")
        if df_ord.empty: st.write("ไม่มีข้อมูล"); return
        
        reserved_orders = df_ord[df_ord['status'] == 'Reserved']
        
        if reserved_orders.empty:
            st.success("✅ ไม่มีรายการรอส่งของ")
        else:
            order_groups = reserved_orders.groupby('id')
            for oid, items in order_groups:
                with st.expander(f"📦 Order: {oid} | ลูกค้า: {items.iloc[0]['customer_name']}"):
                    st.dataframe(items[['code', 'qty', 'status']])
                    
                    if st.button("🚚 ตัดสต็อก & ส่งของ (Ship)", key=f"ship_{oid}"):
                        inv = get_data("Inventory")
                        for _, item in items.iterrows():
                            curr_stock = inv.loc[inv['code'].astype(str) == str(item['code']), 'real_stock'].values[0]
                            new_stock = int(curr_stock) - int(item['qty'])
                            # ตัดสต็อกอย่างเดียว ไม่ยุ่งกับ remark ใน Inventory
                            run_query("update_stock", code=str(item['code']), new_stock=new_stock)
                            
                            ts = str(datetime.datetime.now())
                            today = str(datetime.date.today())
                            log_row = [ts, today, "Ship Order", str(item['code']), "", item['qty'], "", st.session_state['user_name']]
                            append_data("WH_Logs", log_row)
                        
                        run_query("update_order_status", oid=oid, status="Completed")
                        st.success(f"✅ ตัดสต็อก Order {oid} เรียบร้อย!")
                        time.sleep(1)
                        st.rerun()

    # --- TAB 2: Adjust Stock (แก้ใหม่ แยก 3 ปุ่ม) ---
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
                
                # 🟡 โซนที่ 1: จัดการหมายเหตุ (แยกออกมาต่างหาก)
                c_rem1, c_rem2 = st.columns([3, 1])
                remark_val = c_rem1.text_input("📝 แก้ไขหมายเหตุ (Internal Note)", value=str(item['remark']))
                
                if c_rem2.button("💾 บันทึกหมายเหตุ", use_container_width=True):
                    # ส่งไปแค่ remark (Stock ไม่เปลี่ยน)
                    run_query("update_stock", code=str(item['code']), remark=remark_val)
                    st.success("✅ อัปเดตหมายเหตุเรียบร้อย!")
                    time.sleep(1)
                    st.rerun()
                
                st.write("---")
                
                # 🟢 โซนที่ 2: จัดการสต็อก (แยกออกมาต่างหาก)
                adjust_label = f"ระบุจำนวนสินค้า ({item['unit']})"
                adjust_qty = st.number_input(adjust_label, min_value=0, step=1, value=0)
                
                c1, c2 = st.columns(2)
                
                # ปุ่มเพิ่ม (ส่งแค่ new_stock ไม่ส่ง remark)
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

                # ปุ่มลด (ส่งแค่ new_stock ไม่ส่ง remark)
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
            df_log['Date'] = df_log['Date'].astype(str)
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

# ==========================================
# 🚀 MAIN APP LOGIC
# ==========================================
if check_password():
    role = st.session_state['user_role']
    user = st.session_state['user_name']
    
    with st.sidebar:
        # (ส่วนโลโก้เดิมของบอส)
        if os.path.exists("images.png"):
            st.image("images.png", use_container_width=True)
            
        st.title(f"👤 {user}")
        st.caption(f"Role: {role}")
        st.divider()
        
        options = []
        if role == 'WH':
            options = ["5. WH Admin", "6. Support (ช่วยเหลือ)"]
        else:
            # เพิ่มเมนูแคตตาล็อกให้ทุกคนเห็น (ยกเว้น WH อาจจะไม่จำเป็น หรือให้เห็นก็ได้แล้วแต่บอส)
            if role in ['Admin', 'GM', 'CCO', 'Sale-CO', 'Sale']:
                options.append("1. Sale Report")
                options.append("2. Stock & Order")
                options.append("3. Catalogue (ดูสินค้า)") # 🟢 เพิ่มตรงนี้ครับ
            
            if role in ['Admin', 'GM']:
                options.append("4. Manager Approve") # เลื่อนเลขเป็น 4
            if role in ['Admin', 'Sale-CO']:
                options.append("5. Sale-CO (Confirm Reserve)") # เลื่อนเลขเป็น 5
            if role == 'Admin':
                options.append("6. WH Admin") # เลื่อนเลขเป็น 6
            
            options.append("7. Support (ช่วยเหลือ)") # เลื่อนเลขเป็น 7

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
    elif "3." in selected: render_catalogue() # 🟢 เพิ่มทางเดินให้ Catalogue
    elif "4." in selected: render_manager()
    elif "5." in selected: render_saleco()
    elif "6." in selected: render_wh() # ถ้าเป็น Admin จะเข้าอันนี้
    elif "WH Admin" in selected: render_wh() # ถ้าเป็น user WH จะเข้าอันนี้ (ตามเงื่อนไขด้านบน)
    elif "Support" in selected: render_support()



