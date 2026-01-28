import streamlit as st
import pandas as pd
import datetime
import time
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

# 🔐 ข้อมูลผู้ใช้งาน (อัปเดตล่าสุด)
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
        wks.update_cell(cell.row, 4, kwargs['new_stock'])

    elif query_type == "update_order_status":
        wks = sh.worksheet("Orders")
        cell = wks.find(str(kwargs['oid']))
        col_status = 10
        wks.update_cell(cell.row, col_status, kwargs['status'])

    elif query_type == "update_sale_report":
        # Note: การแก้ไขรายงานเก่ายังไม่ได้ทำส่วนคู่แข่งเพิ่ม (เพื่อความง่ายของ Code)
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

# ==========================================
# 🔢 GENERATOR
# ==========================================
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

# ==========================================
# 🔐 AUTHENTICATION
# ==========================================
def check_password():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['user_id'] = None
        st.session_state['user_name'] = None

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
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

# 1. SALE REPORT (Fix: Dropdown คู่แข่ง + Dropdown สินค้า)
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
        
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        t1, t2, t3 = st.columns(3)
        date_visit = t1.date_input("วันที่", datetime.date.today())
        time_in = t2.time_input("เวลาเข้า (Check-in)", value=now.time(), step=60) 
        time_out = t3.time_input("เวลาออก (Check-out)", value=now.time(), step=60)

        obj_options = ["1.เข้าพบ/เยี่ยมลูกค้า", "2.เสนอขายสินค้า", "3.วางบิลเก็บเช็ค", "4.แก้ปัญหา", "5.อื่นๆ"]
        selected_objs = st.multiselect("วัตถุประสงค์", obj_options)
        
        # 🟢 ส่วนที่แก้ใหม่: Dropdown 2 ตัว (คู่แข่ง + สินค้า)
        st.write("---")
        st.write("🕵️ **ข้อมูลคู่แข่ง / ราคาตลาด**")
        
        # 1. โหลดรายชื่อคู่แข่ง
        df_comp = get_data("Competitors")
        comp_list = df_comp['name'].tolist() if not df_comp.empty else []
        comp_list.insert(0, "- ไม่ระบุ -")
        comp_list.append("➕ เพิ่มคู่แข่งใหม่...")
        
        # 2. โหลดรายชื่อสินค้าคู่แข่ง
        df_prod = get_data("Competitor_Products")
        prod_list = df_prod['product_name'].tolist() if not df_prod.empty else []
        prod_list.insert(0, "")
        prod_list.append("➕ เพิ่มสินค้าใหม่...")
        
        col_comp1, col_comp2, col_comp3 = st.columns(3)
        
        # --- ช่องเลือกคู่แข่ง ---
        selected_comp = col_comp1.selectbox("ชื่อคู่แข่ง", comp_list)
        final_comp_name = ""
        if selected_comp == "➕ เพิ่มคู่แข่งใหม่...":
            final_comp_name = col_comp1.text_input("ระบุชื่อคู่แข่งใหม่", placeholder="เช่น BPฟ้า")
        elif selected_comp != "- ไม่ระบุ -":
            final_comp_name = selected_comp
            
        # --- ช่องเลือกสินค้า ---
        selected_prod = col_comp2.selectbox("สินค้าคู่แข่ง", prod_list)
        final_comp_prod = ""
        if selected_prod == "➕ เพิ่มสินค้าใหม่...":
            final_comp_prod = col_comp2.text_input("ระบุสินค้าใหม่", placeholder="เช่น ท่อ 3 นิ้ว")
        elif selected_prod != "":
            final_comp_prod = selected_prod

        # --- ช่องราคา ---
        comp_price = col_comp3.number_input("ราคาที่ลูกค้าซื้อเข้า", min_value=0.0, step=0.1)

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
                    # 🟢 Logic 1: บันทึกชื่อคู่แข่งใหม่ (ถ้ามี)
                    if selected_comp == "➕ เพิ่มคู่แข่งใหม่..." and final_comp_name:
                        if final_comp_name not in comp_list:
                            append_data("Competitors", [final_comp_name])
                    
                    # 🟢 Logic 2: บันทึกชื่อสินค้าใหม่ (ถ้ามี)
                    if selected_prod == "➕ เพิ่มสินค้าใหม่..." and final_comp_prod:
                        if final_comp_prod not in prod_list:
                            append_data("Competitor_Products", [final_comp_prod])

                    final_obj = ", ".join(selected_objs)
                    saved_path = ""
                    if img_file:
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = f"IMG_{ts}.jpg"
                        saved_path = os.path.join(UPLOAD_FOLDER, fname)
                        with open(saved_path, "wb") as f: f.write(img_file.getbuffer())

                    row = [
                        default_doc, str(date_visit), sales_name, cust_name, final_obj, 
                        problem, remark, saved_path, 0, str(datetime.datetime.now()),
                        time_in.strftime("%H:%M"), 
                        time_out.strftime("%H:%M"), 
                        final_comp_name, final_comp_prod, comp_price
                    ]
                    append_data("Sale_Reports", row)
                    st.success(f"✅ บันทึกสำเร็จ: {default_doc}")
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
                        
                        st.write(f"**วัตถุประสงค์:** {row['objective']}")
                        
                        # โชว์ข้อมูลที่ปรับแก้ใหม่
                        if 'comp_name' in row and row['comp_name']:
                            st.info(f"🕵️ **คู่แข่ง:** {row['comp_name']} | สินค้า: {row['comp_product']} | ราคา: {row['comp_price']}")

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
                            
# 2. STOCK & ORDER (อัปเดต: ดูประวัติลูกค้าได้)
def render_stock_order():
    st.header("🛒 Check Stock & Open Order")
    df = get_data("Inventory")
    if df.empty: st.warning("Stock Data Not Found"); return
    
    df_ord = get_data("Orders")
    reserved = pd.DataFrame()
    if not df_ord.empty:
        pending = df_ord[df_ord['status'].isin(['Pending_Manager', 'Pending_SaleCO'])]
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

    search = st.text_input("🔍 ค้นหาสินค้า")
    if search:
        mask = df['name'].astype(str).str.contains(search, case=False) | df['code'].astype(str).str.contains(search, case=False)
        df = df[mask]

    event = st.dataframe(
        df[['code', 'name', 'real_stock', 'reserved_qty', 'available', 'unit']], 
        column_config={
            "real_stock": "Stock", 
            "reserved_qty": "Item reserved", 
            "available": "Ready",
            "unit": "หน่วยนับ"
        },
        use_container_width=True, on_select="rerun", selection_mode="single-row"
    )

    if event.selection.rows:
        item = df.iloc[event.selection.rows[0]]
        st.divider()
        st.subheader(f"เปิดบิล: {item['name']}")
        c1, c2 = st.columns(2)
        s_name = c1.text_input("เซลล์", value=st.session_state['user_name'], disabled=True)
        c_name = c2.text_input("ลูกค้า (พิมพ์เพื่อดูประวัติ)")
        
        # 🟢 ส่วนที่เพิ่มใหม่: ดูประวัติการสั่งซื้อของลูกค้ารายนี้
        if c_name and not df_ord.empty:
            # กรองเฉพาะลูกค้าชื่อนี้
            history = df_ord[df_ord['customer_name'].astype(str).str.contains(c_name, case=False)]
            if not history.empty:
                with st.expander(f"📜 ประวัติการสั่งซื้อของ '{c_name}' ({len(history)} รายการ)"):
                    st.dataframe(
                        history[['date', 'code', 'qty', 'status']], 
                        hide_index=True, use_container_width=True
                    )
            else:
                st.caption("ℹ️ ลูกค้าใหม่ ยังไม่มีประวัติการสั่งซื้อ")

        c3, c4 = st.columns(2)
        qty_label = f"จำนวน ({item['unit']})"
        qty = c3.number_input(qty_label, min_value=1)
        ptype = c4.radio("ราคา", ["Normal", "Special"])
        
        price = 0.0
        if ptype == "Special":
            price = st.number_input("ระบุราคาพิเศษ", min_value=0.0)
            st.warning("⚠️ ต้องรออนุมัติ")

        if st.button("ยืนยันออเดอร์", type="primary"):
            status = "Pending_Manager" if ptype == "Special" else "Pending_SaleCO"
            oid = int(time.time())
            row = [oid, str(datetime.date.today()), s_name, c_name, item['code'], qty, price, qty*price, ptype, status]
            append_data("Orders", row)
            st.success(f"✅ เปิดบิล {qty} {item['unit']} สำเร็จ!")
            st.rerun()

# 3. MANAGER APPROVE
def render_manager():
    st.header("👔 Approval Dashboard")
    df = get_data("Orders")
    if df.empty: st.info("ไม่มีข้อมูล"); return
    pending = df[df['status'] == 'Pending_Manager']
    if pending.empty:
        st.success("✅ ไม่มีรายการค้างอนุมัติ")
        return
    for _, row in pending.iterrows():
        with st.expander(f"Order {row['id']} | {row['sales_person']} -> {row['customer_name']}"):
            st.write(f"สินค้า: {row['code']} จำนวน: {row['qty']}")
            st.write(f"💰 ขอราคาพิเศษ: {row['unit_price']}")
            c1, c2 = st.columns(2)
            if c1.button("อนุมัติ", key=f"app_{row['id']}"):
                run_query("update_order_status", oid=row['id'], status="Pending_SaleCO")
                st.success("Approved!")
                time.sleep(1)
                st.rerun()
            if c2.button("ไม่อนุมัติ", key=f"rej_{row['id']}"):
                run_query("update_order_status", oid=row['id'], status="Cancelled")
                st.error("Rejected!")
                time.sleep(1)
                st.rerun()

# 4. SALE-CO
def render_saleco():
    st.header("👩‍💼 Sale-CO: Cut Stock")
    df = get_data("Orders")
    if df.empty: return
    pending = df[df['status'] == 'Pending_SaleCO']
    if pending.empty: st.info("ไม่มีรายการตัดสต็อก"); return
    for _, row in pending.iterrows():
        with st.expander(f"Order {row['id']} | {row['customer_name']}"):
            st.write(f"สินค้า: {row['code']} จำนวน: {row['qty']}")
            if st.button("✅ ตัดสต็อก & ยืนยัน", key=f"cut_{row['id']}"):
                inv = get_data("Inventory")
                curr_stock = inv.loc[inv['code'].astype(str) == str(row['code']), 'real_stock'].values[0]
                new_stock = int(curr_stock) - int(row['qty'])
                run_query("update_stock", code=str(row['code']), new_stock=new_stock)
                run_query("update_order_status", oid=row['id'], status="Confirmed")
                st.success("ตัดสต็อกเรียบร้อย!")
                time.sleep(1)
                st.rerun()

# 5. WH ADMIN
def render_wh():
    st.header("🏭 Warehouse Management")
    tab1, tab2 = st.tabs(["✏️ Adjust Stock", "📂 Upload Excel"])
    with tab1:
        df = get_data("Inventory")
        if not df.empty:
            search = st.text_input("ค้นหา:", placeholder="Code/Name")
            if search: 
                mask = df['code'].astype(str).str.contains(search, case=False) | df['name'].astype(str).str.contains(search, case=False)
                df = df[mask]
            event = st.dataframe(df[['code','name','real_stock','unit']], column_config={"unit": "หน่วยนับ"}, on_select="rerun", selection_mode="single-row", use_container_width=True)
            if event.selection.rows:
                item = df.iloc[event.selection.rows[0]]
                st.info(f"สินค้า: {item['name']} | 📦 ของเดิม: {item['real_stock']} {item['unit']}")
                adjust_label = f"ระบุจำนวนสินค้า ({item['unit']})"
                adjust_qty = st.number_input(adjust_label, min_value=0, step=1, value=0)
                c1, c2 = st.columns(2)
                if c1.button("➕ เพิ่ม Stock (รับเข้า)", use_container_width=True, type="primary"):
                    if adjust_qty > 0:
                        new_val = int(item['real_stock']) + adjust_qty
                        run_query("update_stock", code=str(item['code']), new_stock=new_val)
                        st.success(f"✅ รับเข้า {adjust_qty} {item['unit']} เรียบร้อย! (ยอดใหม่: {new_val} {item['unit']})")
                        time.sleep(1)
                        st.rerun()
                    else: st.warning("ระบุจำนวน > 0")
                if c2.button("➖ ตัด Stock (จ่ายออก)", use_container_width=True):
                    if adjust_qty > 0:
                        new_val = int(item['real_stock']) - adjust_qty
                        run_query("update_stock", code=str(item['code']), new_stock=new_val)
                        st.warning(f"🔻 จ่ายออก {adjust_qty} {item['unit']} เรียบร้อย! (ยอดใหม่: {new_val} {item['unit']})")
                        time.sleep(1)
                        st.rerun()
                    else: st.warning("ระบุจำนวน > 0")
    with tab2:
        st.warning("⚠️ การ Upload Excel จะลบข้อมูลเดิมทั้งหมด!")
        up = st.file_uploader("เลือกไฟล์ Excel Stock (.xlsx)", type=['xlsx'])
        if up and st.button("🚀 เริ่มอัปโหลด"):
            try:
                df_new = pd.read_excel(up)
                df_new.columns = df_new.columns.str.strip()
                df_new['Stock'] = pd.to_numeric(df_new['Stock'], errors='coerce').fillna(0)
                df_new = df_new.fillna("")
                upload_data = []
                for _, r in df_new.iterrows():
                    row = [str(r['code']), str(r['กลุ่ม']), str(r['รายละเอียด']), int(r['Stock']), str(r['หน่วยนับขนาน'])]
                    upload_data.append(row)
                client = get_gsheet_client()
                wks = client.open(SHEET_NAME).worksheet("Inventory")
                wks.clear()
                wks.append_row(['code', 'category', 'name', 'real_stock', 'unit'])
                wks.append_rows(upload_data)
                st.success(f"✅ อัปโหลดสำเร็จ {len(upload_data)} รายการ!")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

# 6. SUPPORT
def render_support():
    st.header("🆘 Support & Nearby Services")
    st.write("ค้นหาสถานที่อำนวยความสะดวกใกล้ตัวคุณ")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🏨 โรงแรมใกล้ฉัน", "https://www.google.com/maps/search/hotels+near+me", use_container_width=True)
        st.link_button("⛽ ปั๊มน้ำมันใกล้ฉัน", "https://www.google.com/maps/search/gas+station+near+me", use_container_width=True)
    with col2:
        st.link_button("🍽️ ร้านอาหารใกล้ฉัน", "https://www.google.com/maps/search/restaurants+near+me", use_container_width=True)
        st.link_button("🏥 โรงพยาบาลใกล้ฉัน", "https://www.google.com/maps/search/hospitals+near+me", use_container_width=True)

# ==========================================
# 🚀 MAIN APP LOGIC
# ==========================================
if check_password():
    role = st.session_state['user_role']
    user = st.session_state['user_name']
    
    with st.sidebar:
        st.title(f"👤 {user}")
        st.caption(f"Role: {role}")
        st.divider()
        options = []
        if role == 'WH':
            options = ["5. WH Admin", "6. Support (ช่วยเหลือ)"]
        else:
            if role in ['Admin', 'GM', 'CCO', 'Sale-CO', 'Sale']:
                options.append("1. Sale Report")
                options.append("2. Stock & Order")
            if role in ['Admin', 'GM']:
                options.append("3. Manager Approve")
            if role in ['Admin', 'Sale-CO']:
                options.append("4. Sale-CO (Cut Stock)")
            if role == 'Admin':
                options.append("5. WH Admin")
            options.append("6. Support (ช่วยเหลือ)")

        if options:
            selected = st.radio("เมนูใช้งาน", options)
            st.divider()
            if st.button("Logout"): logout()
        else:
            st.error("Access Denied")
            if st.button("Logout"): logout()

    # Router
    if "1." in selected: render_sale_report()
    elif "2." in selected: render_stock_order()
    elif "3." in selected: render_manager()
    elif "4." in selected: render_saleco()
    elif "5." in selected: render_wh()
    elif "6." in selected: render_support()


