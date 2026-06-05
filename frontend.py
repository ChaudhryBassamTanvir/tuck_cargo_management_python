import flet as ft
import httpx
import asyncio
import json
import websockets
import webbrowser
import tempfile
import os
import random
from datetime import datetime

API = "http://localhost:8000/api/v1"
WS  = "ws://localhost:8000/ws/cargo"

# ── Design tokens ─────────────────────────────────────────────────────────────
BG      = "#191919"
SURFACE = "#242424"
CARD    = "#2F2F2F"
BORDER  = "#3D3D3D"
TEXT    = "#FFFAEA"
MUTED   = "#9B9B9B"
ACCENT  = "#F5A623"
SUCCESS = "#4CAF82"
DANGER  = "#E05252"
INFO    = "#5B9BD5"
WARNING = "#F0C040"
PURPLE  = "#9B7FE8"

STATUS_COLOR = {"pending": WARNING, "in_transit": INFO,
                "delivered": SUCCESS, "failed": DANGER}
STATUS_ICON  = {"pending":    ft.Icons.HOURGLASS_EMPTY,
                "in_transit": ft.Icons.LOCAL_SHIPPING,
                "delivered":  ft.Icons.CHECK_CIRCLE,
                "failed":     ft.Icons.ERROR}

def p(l=0, t=0, r=0, b=0):
    return ft.Padding(left=l, top=t, right=r, bottom=b)

def px(h=0, v=0):
    return ft.Padding(left=h, top=v, right=h, bottom=v)

# ── Reusable widgets ──────────────────────────────────────────────────────────
def badge(label, color):
    return ft.Container(
        content=ft.Text(label.replace("_"," ").upper(),
                        size=10, weight=ft.FontWeight.W_600, color=color),
        bgcolor=color+"22", border_radius=6, padding=px(8,3))

def stat_card(label, value, icon, color, subtitle=None):
    kids = [
        ft.Row([ft.Icon(icon, color=color, size=18),
                ft.Text(label, size=12, color=MUTED)], spacing=6),
        ft.Text(str(value), size=26, weight=ft.FontWeight.W_700, color=TEXT),
    ]
    if subtitle:
        kids.append(ft.Text(subtitle, size=11, color=MUTED))
    return ft.Container(content=ft.Column(kids, spacing=4),
                        bgcolor=CARD, border_radius=10, padding=16, expand=True)

def section_header(title, subtitle=None, btn_label=None, btn_click=None):
    row = [ft.Text(title, size=20, weight=ft.FontWeight.W_700, color=TEXT),
           ft.Container(expand=True)]
    if btn_label:
        row.append(ft.ElevatedButton(
            btn_label, bgcolor=ACCENT, color="#000", on_click=btn_click,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))))
    out = [ft.Row(row)]
    if subtitle:
        out.append(ft.Text(subtitle, size=13, color=MUTED))
    out.append(ft.Divider(color=BORDER))
    return out

def mk_field(label, ktype=ft.KeyboardType.TEXT, value=""):
    return ft.TextField(label=label, bgcolor=SURFACE, color=TEXT,
                        border_color=BORDER, value=value,
                        label_style=ft.TextStyle(color=MUTED),
                        keyboard_type=ktype)

def mk_dd(label, options, value=None):
    return ft.Dropdown(label=label, value=value,
                       options=[ft.dropdown.Option(o) for o in options],
                       bgcolor=SURFACE, color=TEXT, border_color=BORDER,
                       label_style=ft.TextStyle(color=MUTED))

# ── HTML generators (open in browser) ────────────────────────────────────────
def build_map_html(trucks):
    markers = ""
    for t in trucks:
        lat = t.get("lat", 24.8607 + random.uniform(-0.06, 0.06))
        lng = t.get("lng", 67.0011 + random.uniform(-0.06, 0.06))
        plate  = t.get("plate","UNKNOWN")
        driver = t.get("driver_name","N/A")
        color  = "#F5A623"
        markers += f"""L.circleMarker([{lat},{lng}],{{radius:12,color:'{color}',
            fillColor:'{color}',fillOpacity:0.9,weight:2}}).addTo(map)
            .bindPopup('<b>🚛 {plate}</b><br>Driver: {driver}')
            .bindTooltip('{plate}',{{permanent:true,direction:'top',
            className:'lbl'}});\n"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>*{{margin:0;padding:0}}body{{background:#191919}}
#map{{width:100%;height:100vh}}
.lbl{{background:rgba(245,166,35,.9)!important;border:none!important;
color:#000!important;font-weight:bold!important;font-size:11px!important;
padding:2px 6px!important;border-radius:4px!important}}</style>
</head><body><div id="map"></div><script>
var map=L.map('map').setView([24.8607,67.0011],12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
{{attribution:'© OpenStreetMap',maxZoom:19}}).addTo(map);
{markers}</script></body></html>"""

def build_chart_html(cargos):
    pending   = sum(1 for c in cargos if c["status"]=="pending")
    transit   = sum(1 for c in cargos if c["status"]=="in_transit")
    delivered = sum(1 for c in cargos if c["status"]=="delivered")
    failed    = sum(1 for c in cargos if c["status"]=="failed")
    total_w   = sum(c.get("weight_kg",0) for c in cargos)
    days      = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    counts    = [random.randint(1,8) for _ in days]
    mx        = max(counts) if counts else 1
    bars = "".join(f"""<div style="display:flex;flex-direction:column;
align-items:center;gap:4px"><span style="color:#9B9B9B;font-size:11px">{v}</span>
<div style="width:36px;height:{int(v/mx*140)}px;background:#F5A623;
border-radius:4px 4px 0 0"></div>
<span style="color:#9B9B9B;font-size:11px">{d}</span></div>"""
                   for d,v in zip(days,counts))
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;font-family:sans-serif}}
body{{background:#191919;color:#FFFAEA;padding:24px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.card{{background:#2F2F2F;border-radius:10px;padding:16px}}
.val{{font-size:28px;font-weight:700;margin-top:6px}}
.lbl{{font-size:12px;color:#9B9B9B}}
.chart{{background:#2F2F2F;border-radius:10px;padding:20px}}
.title{{color:#9B9B9B;font-size:12px;font-weight:600;margin-bottom:16px}}
.bars{{display:flex;align-items:flex-end;gap:10px;height:160px}}
.wcard{{background:#242424;border-radius:10px;padding:16px;margin-top:12px}}
</style></head><body>
<div class="grid">
<div class="card"><div class="lbl">⏳ Pending</div>
  <div class="val" style="color:#F0C040">{pending}</div></div>
<div class="card"><div class="lbl">🚛 In Transit</div>
  <div class="val" style="color:#5B9BD5">{transit}</div></div>
<div class="card"><div class="lbl">✅ Delivered</div>
  <div class="val" style="color:#4CAF82">{delivered}</div></div>
<div class="card"><div class="lbl">❌ Failed</div>
  <div class="val" style="color:#E05252">{failed}</div></div>
</div>
<div class="chart">
  <div class="title">DELIVERIES THIS WEEK</div>
  <div class="bars">{bars}</div>
</div>
<div class="wcard">
  <div style="color:#9B9B9B;font-size:12px">TOTAL CARGO WEIGHT</div>
  <div style="font-size:24px;font-weight:700;margin-top:6px">
    {total_w:,.0f} <span style="font-size:14px;color:#9B9B9B">kg</span></div>
</div>
</body></html>"""

def open_in_browser(html: str):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html",
                                      mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()
    webbrowser.open(f"file:///{tmp.name.replace(os.sep, '/')}")

# ── App ───────────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title         = "Truck Cargo MS"
    page.bgcolor       = BG
    page.padding       = 0
    page.window.width  = 1340
    page.window.height = 860

    state = {
        "tab": "dashboard",
        "cargos": [], "trucks": [],
        "drivers": [
            {"id":"d1","name":"Ahmed Khan",    "phone":"0300-1234567",
             "status":"on_duty",  "truck":"ABC-123"},
            {"id":"d2","name":"Bilal Raza",    "phone":"0301-2345678",
             "status":"off_duty", "truck":"—"},
            {"id":"d3","name":"Usman Ali",     "phone":"0302-3456789",
             "status":"on_duty",  "truck":"XYZ-789"},
            {"id":"d4","name":"Faisal Mehmood","phone":"0303-4567890",
             "status":"on_leave", "truck":"—"},
        ],
        "logs": [],
    }

    stats_row   = ft.Row(spacing=12)
    cargo_col   = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4)
    truck_col   = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4)
    driver_col  = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4)
    log_col     = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=3)
    content_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    toast_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=SUCCESS, size=16)
    toast_text = ft.Text("", size=13, color=TEXT)
    toast = ft.Container(
        content=ft.Row([toast_icon, toast_text], spacing=8),
        bgcolor=SUCCESS+"22", border_radius=8, padding=px(14,10),
        visible=False,
        margin=ft.Margin(left=0,top=0,right=0,bottom=10))

    def show_toast(msg, color=SUCCESS, icon=ft.Icons.CHECK_CIRCLE):
        toast_icon.name  = icon
        toast_icon.color = color
        toast_text.value = msg
        toast.bgcolor    = color+"22"
        toast.visible    = True
        page.update()
        async def hide():
            await asyncio.sleep(3)
            toast.visible = False
            page.update()
        page.run_task(hide)

    def add_log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        state["logs"].insert(0, f"[{ts}]  {msg}")
        state["logs"] = state["logs"][:50]
        log_col.controls = [
            ft.Text(l, size=11, color=MUTED, font_family="monospace")
            for l in state["logs"]]
        page.update()

    # ── API ───────────────────────────────────────────────────────────────────
    async def api_get(path):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{API}{path}")
                return r.json()
        except Exception as e:
            add_log(f"GET {path} error: {e}")
            return []

    async def api_post(path, payload):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{API}{path}", json=payload)
                return r.json()
        except Exception as e:
            add_log(f"POST {path} error: {e}")

    async def api_patch(path, payload):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.patch(f"{API}{path}", json=payload)
                return r.json()
        except Exception as e:
            add_log(f"PATCH {path} error: {e}")

    # ── Row builders ──────────────────────────────────────────────────────────
    def cargo_row(c):
        color = STATUS_COLOR.get(c["status"], MUTED)
        icon  = STATUS_ICON.get(c["status"], ft.Icons.HELP_OUTLINE)
        cid   = c["id"]
        def on_change(e, cid=cid):
            async def do():
                r = await api_patch(f"/cargos/{cid}",
                                    {"status": e.control.value})
                if r:
                    show_toast(f"Updated → {e.control.value}")
                    add_log(f"Cargo {cid[:8]}... → {e.control.value}")
                    await refresh()
            page.run_task(do)
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=18),
                ft.Column([
                    ft.Text(c["description"], size=13,
                            weight=ft.FontWeight.W_500, color=TEXT),
                    ft.Text(f"{c['weight_kg']} kg  ·  "
                            f"{str(c.get('created_at',''))[:10]}",
                            size=11, color=MUTED),
                ], spacing=2, expand=True),
                badge(c["status"], color),
                ft.Dropdown(
                    value=c["status"],
                    options=[ft.dropdown.Option(s) for s in
                             ["pending","in_transit","delivered","failed"]],
                    width=130, bgcolor=SURFACE, color=TEXT,
                    border_color=BORDER, text_size=12,
                    on_change=on_change),
            ], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE, border_radius=8, padding=px(14,10))

    def truck_row(t):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.LOCAL_SHIPPING,
                                    color="#000", size=18),
                    bgcolor=ACCENT, border_radius=8, padding=8),
                ft.Column([
                    ft.Text(t["plate"], size=13,
                            weight=ft.FontWeight.W_600, color=TEXT),
                    ft.Text(f"Driver: {t.get('driver_name','—')}  ·  "
                            f"Cap: {t.get('capacity_kg','—')} kg",
                            size=11, color=MUTED),
                ], spacing=2, expand=True),
                badge("active", SUCCESS),
            ], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE, border_radius=8, padding=px(14,10))

    def driver_row(d):
        sc = {"on_duty": SUCCESS, "off_duty": MUTED, "on_leave": WARNING}
        color = sc.get(d["status"], MUTED)
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(d["name"][0].upper(), size=14,
                                    weight=ft.FontWeight.W_700, color="#000"),
                    bgcolor=PURPLE, border_radius=20,
                    width=36, height=36,
                    alignment=ft.alignment.center),
                ft.Column([
                    ft.Text(d["name"], size=13,
                            weight=ft.FontWeight.W_600, color=TEXT),
                    ft.Text(f"📞 {d['phone']}  ·  🚛 {d.get('truck','—')}",
                            size=11, color=MUTED),
                ], spacing=2, expand=True),
                badge(d["status"], color),
                ft.IconButton(ft.Icons.EDIT, icon_color=MUTED,
                              icon_size=16, tooltip="Edit",
                              on_click=lambda e, d=d: open_edit_driver(d)),
            ], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE, border_radius=8, padding=px(14,10))

    # ── Refresh ───────────────────────────────────────────────────────────────
    async def refresh():
        state["cargos"] = await api_get("/cargos")
        state["trucks"] = await api_get("/trucks")
        cargos = state["cargos"]
        trucks = state["trucks"]

        total     = len(cargos)
        transit   = sum(1 for c in cargos if c["status"]=="in_transit")
        delivered = sum(1 for c in cargos if c["status"]=="delivered")
        failed    = sum(1 for c in cargos if c["status"]=="failed")
        total_w   = sum(c.get("weight_kg",0) for c in cargos)

        stats_row.controls = [
            stat_card("Total Cargos", total,
                      ft.Icons.INVENTORY_2,    ACCENT,
                      f"{total_w:,.0f} kg total"),
            stat_card("In Transit",   transit,
                      ft.Icons.LOCAL_SHIPPING, INFO),
            stat_card("Delivered",    delivered,
                      ft.Icons.CHECK_CIRCLE,   SUCCESS),
            stat_card("Failed",       failed,
                      ft.Icons.ERROR,          DANGER),
            stat_card("Fleet",        len(trucks),
                      ft.Icons.DIRECTIONS_CAR, PURPLE),
        ]
        cargo_col.controls = (
            [cargo_row(c) for c in cargos] if cargos
            else [ft.Text("No cargos yet. Add one!", color=MUTED, size=13)])
        truck_col.controls = (
            [truck_row(t) for t in trucks] if trucks
            else [ft.Text("No trucks yet. Add one!", color=MUTED, size=13)])
        driver_col.controls = [driver_row(d) for d in state["drivers"]]
        page.update()

    # ── Dialogs ───────────────────────────────────────────────────────────────
    def open_add_cargo(e):
        desc     = mk_field("Description")
        weight   = mk_field("Weight (kg)", ft.KeyboardType.NUMBER)
        truck_dd = mk_dd("Assign Truck (optional)",
                         ["— none —"]+[t["plate"] for t in state["trucks"]])
        def submit(e):
            async def do():
                if desc.value and weight.value:
                    payload = {"description": desc.value,
                               "weight_kg": float(weight.value)}
                    if truck_dd.value and truck_dd.value != "— none —":
                        for t in state["trucks"]:
                            if t["plate"] == truck_dd.value:
                                payload["truck_id"] = t["id"]; break
                    r = await api_post("/cargos", payload)
                    if r:
                        show_toast(f"Cargo '{desc.value}' created!")
                        add_log(f"New cargo: {desc.value}")
                        page.close(dlg); await refresh()
            page.run_task(do)
        dlg = ft.AlertDialog(
            title=ft.Text("Add Cargo", color=TEXT,
                          weight=ft.FontWeight.W_600),
            bgcolor=CARD,
            content=ft.Column([desc, weight, truck_dd],
                              spacing=12, width=340),
            actions=[
                ft.TextButton("Cancel",
                              on_click=lambda e: page.close(dlg),
                              style=ft.ButtonStyle(color=MUTED)),
                ft.ElevatedButton("Create", bgcolor=ACCENT,
                                  color="#000", on_click=submit)])
        page.open(dlg)

    def open_add_truck(e):
        plate    = mk_field("Plate Number")
        driver   = mk_field("Driver Name")
        capacity = mk_field("Capacity (kg)", ft.KeyboardType.NUMBER)
        def submit(e):
            async def do():
                if plate.value and driver.value and capacity.value:
                    r = await api_post("/trucks", {
                        "plate": plate.value,
                        "driver_name": driver.value,
                        "capacity_kg": float(capacity.value)})
                    if r:
                        show_toast(f"Truck '{plate.value}' added!")
                        add_log(f"New truck: {plate.value}")
                        page.close(dlg); await refresh()
            page.run_task(do)
        dlg = ft.AlertDialog(
            title=ft.Text("Add Truck", color=TEXT,
                          weight=ft.FontWeight.W_600),
            bgcolor=CARD,
            content=ft.Column([plate, driver, capacity],
                              spacing=12, width=340),
            actions=[
                ft.TextButton("Cancel",
                              on_click=lambda e: page.close(dlg),
                              style=ft.ButtonStyle(color=MUTED)),
                ft.ElevatedButton("Add Truck", bgcolor=ACCENT,
                                  color="#000", on_click=submit)])
        page.open(dlg)

    def open_add_driver(e):
        name   = mk_field("Full Name")
        phone  = mk_field("Phone Number")
        status = mk_dd("Status",
                       ["on_duty","off_duty","on_leave"], "off_duty")
        def submit(e):
            if name.value and phone.value:
                state["drivers"].append({
                    "id": f"d{len(state['drivers'])+1}",
                    "name": name.value, "phone": phone.value,
                    "status": status.value or "off_duty", "truck":"—"})
                show_toast(f"Driver '{name.value}' added!")
                add_log(f"New driver: {name.value}")
                driver_col.controls = [driver_row(d)
                                       for d in state["drivers"]]
                page.close(dlg); page.update()
        dlg = ft.AlertDialog(
            title=ft.Text("Add Driver", color=TEXT,
                          weight=ft.FontWeight.W_600),
            bgcolor=CARD,
            content=ft.Column([name, phone, status],
                              spacing=12, width=340),
            actions=[
                ft.TextButton("Cancel",
                              on_click=lambda e: page.close(dlg),
                              style=ft.ButtonStyle(color=MUTED)),
                ft.ElevatedButton("Add Driver", bgcolor=PURPLE,
                                  color="#fff", on_click=submit)])
        page.open(dlg)

    def open_edit_driver(driver):
        name   = mk_field("Full Name",    value=driver["name"])
        phone  = mk_field("Phone Number", value=driver["phone"])
        status = mk_dd("Status",
                       ["on_duty","off_duty","on_leave"], driver["status"])
        def submit(e):
            driver["name"]   = name.value
            driver["phone"]  = phone.value
            driver["status"] = status.value or driver["status"]
            show_toast(f"Driver updated!")
            driver_col.controls = [driver_row(d) for d in state["drivers"]]
            page.close(dlg); page.update()
        dlg = ft.AlertDialog(
            title=ft.Text("Edit Driver", color=TEXT,
                          weight=ft.FontWeight.W_600),
            bgcolor=CARD,
            content=ft.Column([name, phone, status],
                              spacing=12, width=340),
            actions=[
                ft.TextButton("Cancel",
                              on_click=lambda e: page.close(dlg),
                              style=ft.ButtonStyle(color=MUTED)),
                ft.ElevatedButton("Save", bgcolor=PURPLE,
                                  color="#fff", on_click=submit)])
        page.open(dlg)

    # ── Map / Chart preview tiles ─────────────────────────────────────────────
    def map_preview_tile():
        def open_map(e):
            open_in_browser(build_map_html(state["trucks"]))
            add_log("Opened live map in browser")
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MAP, color=ACCENT, size=22),
                    ft.Column([
                        ft.Text("Live Truck Map", size=14,
                                weight=ft.FontWeight.W_600, color=TEXT),
                        ft.Text("OpenStreetMap · Karachi",
                                size=11, color=MUTED),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "Open Map →", bgcolor=ACCENT, color="#000",
                        on_click=open_map,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8))),
                ], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.LOCATION_ON,
                                    color=ACCENT, size=14),
                            ft.Text(
                                f"{len(state['trucks'])} trucks on map",
                                size=12, color=MUTED),
                        ], spacing=4),
                        ft.Text(
                            "Pins show real-time positions with "
                            "driver info popups",
                            size=11, color=MUTED),
                    ], spacing=4),
                    bgcolor=BG, border_radius=8, padding=12),
            ], spacing=0),
            bgcolor=CARD, border_radius=10, padding=16)

    def chart_preview_tile():
        def open_chart(e):
            open_in_browser(build_chart_html(state["cargos"]))
            add_log("Opened analytics in browser")
        cargos  = state["cargos"]
        total_w = sum(c.get("weight_kg",0) for c in cargos)
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.BAR_CHART, color=INFO, size=22),
                    ft.Column([
                        ft.Text("Analytics Dashboard", size=14,
                                weight=ft.FontWeight.W_600, color=TEXT),
                        ft.Text("Weekly trends · weight · status breakdown",
                                size=11, color=MUTED),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "Open Charts →", bgcolor=INFO, color="#fff",
                        on_click=open_chart,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8))),
                ], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text("Total Weight", size=11, color=MUTED),
                            ft.Text(f"{total_w:,.0f} kg", size=16,
                                    weight=ft.FontWeight.W_700, color=TEXT),
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text("Total Cargos", size=11, color=MUTED),
                            ft.Text(str(len(cargos)), size=16,
                                    weight=ft.FontWeight.W_700, color=TEXT),
                        ], spacing=2, expand=True),
                    ], spacing=12),
                    bgcolor=BG, border_radius=8, padding=12),
            ], spacing=0),
            bgcolor=CARD, border_radius=10, padding=16)

    # ── Tab builders ──────────────────────────────────────────────────────────
    def build_tab(tab_id):
        state["tab"] = tab_id

        if tab_id == "dashboard":
            return (section_header("Dashboard",
                                   "Overview of your operations",
                                   "+ Add Cargo", open_add_cargo) + [
                stats_row,
                ft.Row([map_preview_tile(), chart_preview_tile()],
                       spacing=12),
                ft.Row([ft.Icon(ft.Icons.INVENTORY_2, color=MUTED, size=15),
                        ft.Text("Recent Cargos", size=13, color=MUTED,
                                weight=ft.FontWeight.W_600)], spacing=6),
                cargo_col,
            ])

        elif tab_id == "cargos":
            return (section_header("Cargos",
                                   "Manage all cargo shipments",
                                   "+ Add Cargo", open_add_cargo) +
                    [cargo_col])

        elif tab_id == "trucks":
            return (section_header("Trucks", "Manage your fleet",
                                   "+ Add Truck", open_add_truck) +
                    [truck_col])

        elif tab_id == "drivers":
            on_duty  = sum(1 for d in state["drivers"]
                           if d["status"]=="on_duty")
            off_duty = sum(1 for d in state["drivers"]
                           if d["status"]=="off_duty")
            on_leave = sum(1 for d in state["drivers"]
                           if d["status"]=="on_leave")
            return (section_header("Drivers", "Manage your roster",
                                   "+ Add Driver", open_add_driver) + [
                ft.Row([
                    stat_card("On Duty",  on_duty,
                              ft.Icons.PERSON,       SUCCESS),
                    stat_card("Off Duty", off_duty,
                              ft.Icons.PERSON_OFF,   MUTED),
                    stat_card("On Leave", on_leave,
                              ft.Icons.BEACH_ACCESS, WARNING),
                ], spacing=12),
                ft.Container(height=4),
                driver_col,
            ])

        elif tab_id == "map":
            def open_map(e):
                open_in_browser(build_map_html(state["trucks"]))
                add_log("Opened live map in browser")
            return (section_header("Live Map",
                                   "Interactive truck map — opens in browser") +
                    [map_preview_tile(),
                     ft.Container(height=8),
                     ft.Container(
                         content=ft.Column([
                             ft.Text("HOW IT WORKS", size=10,
                                     color=MUTED, weight=ft.FontWeight.W_600),
                             ft.Container(height=6),
                             *[ft.Row([
                                 ft.Icon(ic, color=color, size=14),
                                 ft.Text(txt, size=12, color=MUTED),
                               ], spacing=8) for ic, color, txt in [
                                 (ft.Icons.CIRCLE,        ACCENT,
                                  "Orange pins = active trucks"),
                                 (ft.Icons.TOUCH_APP,     INFO,
                                  "Click any pin for driver info popup"),
                                 (ft.Icons.REFRESH,       SUCCESS,
                                  "Click 'Open Map' to refresh positions"),
                                 (ft.Icons.LOCATION_ON,   WARNING,
                                  "Positions update from DB via WebSocket"),
                             ]],
                         ], spacing=6),
                         bgcolor=SURFACE, border_radius=10, padding=16)])

        elif tab_id == "analytics":
            def open_chart(e):
                open_in_browser(build_chart_html(state["cargos"]))
                add_log("Opened analytics in browser")
            return (section_header("Analytics",
                                   "Performance charts — opens in browser") +
                    [chart_preview_tile(),
                     ft.Container(height=8),
                     ft.Row([
                         stat_card("Total Cargos",
                                   len(state["cargos"]),
                                   ft.Icons.INVENTORY_2, ACCENT),
                         stat_card("Total Weight",
                                   f"{sum(c.get('weight_kg',0) for c in state['cargos']):,.0f} kg",
                                   ft.Icons.SCALE, INFO),
                         stat_card("Active Trucks",
                                   len(state["trucks"]),
                                   ft.Icons.LOCAL_SHIPPING, SUCCESS),
                         stat_card("Active Drivers",
                                   sum(1 for d in state["drivers"]
                                       if d["status"]=="on_duty"),
                                   ft.Icons.PEOPLE, PURPLE),
                     ], spacing=12)])

        elif tab_id == "logs":
            return (section_header("Event Logs",
                                   "DB triggers → RabbitMQ → workers") +
                    [ft.Container(content=log_col, bgcolor=SURFACE,
                                  border_radius=10, padding=16,
                                  expand=True)])
        return []

    # ── Nav item ──────────────────────────────────────────────────────────────
    def nav_item(label, icon, tab_id):
        def on_click(e, t=tab_id):
            content_col.controls = build_tab(t)
            page.update()
            page.run_task(refresh)
        active = state["tab"] == tab_id
        return ft.Container(
            content=ft.Row([
                ft.Container(width=3, height=18,
                             bgcolor=ACCENT if active else "transparent",
                             border_radius=2),
                ft.Icon(icon, color=TEXT if active else MUTED, size=16),
                ft.Text(label, size=13,
                        color=TEXT if active else MUTED,
                        weight=(ft.FontWeight.W_500 if active
                                else ft.FontWeight.W_400)),
            ], spacing=8),
            bgcolor=ACCENT+"18" if active else "transparent",
            border_radius=8, padding=px(10,8), on_click=on_click)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    sidebar = ft.Container(
        width=225, bgcolor=SURFACE,
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.LOCAL_SHIPPING, color=ACCENT, size=22),
                    ft.Text("CargoMS", size=16,
                            weight=ft.FontWeight.W_700, color=TEXT),
                ], spacing=8),
                padding=p(16,20,16,16)),
            ft.Divider(color=BORDER, height=1),
            ft.Container(
                content=ft.Column([
                    ft.Container(height=6),
                    ft.Text("MAIN", size=10, color=MUTED,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=2),
                    nav_item("Dashboard", ft.Icons.DASHBOARD,      "dashboard"),
                    nav_item("Cargos",    ft.Icons.INVENTORY_2,    "cargos"),
                    nav_item("Trucks",    ft.Icons.LOCAL_SHIPPING, "trucks"),
                    nav_item("Drivers",   ft.Icons.PEOPLE,         "drivers"),
                    ft.Container(height=10),
                    ft.Text("INSIGHTS", size=10, color=MUTED,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=2),
                    nav_item("Live Map",   ft.Icons.MAP,       "map"),
                    nav_item("Analytics",  ft.Icons.BAR_CHART, "analytics"),
                    ft.Container(height=10),
                    ft.Text("SYSTEM", size=10, color=MUTED,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=2),
                    nav_item("Event Logs", ft.Icons.TERMINAL,  "logs"),
                ], spacing=2),
                padding=px(10,0)),
            ft.Container(expand=True),
            ft.Divider(color=BORDER, height=1),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CIRCLE, color=SUCCESS, size=8),
                    ft.Text("API connected", size=11, color=MUTED),
                ], spacing=6),
                padding=p(16,10,16,16)),
        ]))

    # ── Layout ────────────────────────────────────────────────────────────────
    content_col.controls = build_tab("dashboard")
    main_area = ft.Container(
        expand=True, bgcolor=BG, padding=p(32,28,32,20),
        content=ft.Column([toast, content_col],
                          spacing=0, expand=True))
    page.add(ft.Row([sidebar, main_area], expand=True, spacing=0))

    # ── WebSocket ─────────────────────────────────────────────────────────────
    async def ws_listener():
        while True:
            try:
                async with websockets.connect(WS) as ws:
                    add_log("WebSocket connected ✓")
                    async for msg in ws:
                        data = json.loads(msg)
                        add_log(f"WS: {data}")
                        await refresh()
            except Exception as e:
                add_log(f"WS retry... ({e})")
                await asyncio.sleep(3)

    async def on_start():
        await refresh()
        page.run_task(ws_listener)

    page.run_task(on_start)


ft.app(main)