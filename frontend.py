import flet as ft
import httpx
import asyncio
import json
import websockets
from datetime import datetime

API = "http://localhost:8000/api/v1"
WS  = "ws://localhost:8000/ws/cargo"

# ── Reusable color tokens ─────────────────────────────────────────────────────
BG        = "#191919"
SURFACE   = "#242424"
CARD      = "#2F2F2F"
BORDER    = "#3D3D3D"
TEXT      = "#FFFAEA"
MUTED     = "#9B9B9B"
ACCENT    = "#F5A623"
SUCCESS   = "#4CAF82"
DANGER    = "#E05252"
INFO      = "#5B9BD5"
WARNING   = "#F0C040"

STATUS_COLOR = {
    "pending":    WARNING,
    "in_transit": INFO,
    "delivered":  SUCCESS,
    "failed":     DANGER,
}
STATUS_ICON = {
    "pending":    ft.icons.HOURGLASS_EMPTY_ROUNDED,
    "in_transit": ft.icons.LOCAL_SHIPPING_ROUNDED,
    "delivered":  ft.icons.CHECK_CIRCLE_ROUNDED,
    "failed":     ft.icons.ERROR_ROUNDED,
}

# ── Reusable components ───────────────────────────────────────────────────────
def badge(label: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label.replace("_", " ").upper(), size=10, weight=ft.FontWeight.W_600, color=color),
        bgcolor=f"{color}22",
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        border=ft.border.all(1, f"{color}55"),
    )

def icon_btn(icon, tooltip, on_click, color=MUTED) -> ft.IconButton:
    return ft.IconButton(icon=icon, icon_color=color, tooltip=tooltip,
                         icon_size=16, on_click=on_click,
                         style=ft.ButtonStyle(padding=ft.padding.all(4)))

def divider() -> ft.Divider:
    return ft.Divider(height=1, color=BORDER)

def section_title(text: str, icon=None) -> ft.Row:
    controls = []
    if icon:
        controls.append(ft.Icon(icon, color=MUTED, size=16))
    controls.append(ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=MUTED))
    return ft.Row(controls, spacing=6)

def card(content) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=CARD,
        border_radius=10,
        padding=16,
        border=ft.border.all(1, BORDER),
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

def stat_card(label, value, icon, color) -> ft.Container:
    return ft.Container(
        content=ft.Column([
            ft.Row([ft.Icon(icon, color=color, size=20),
                    ft.Text(label, size=12, color=MUTED)], spacing=6),
            ft.Text(str(value), size=28, weight=ft.FontWeight.W_700, color=TEXT),
        ], spacing=4),
        bgcolor=CARD,
        border_radius=10,
        padding=16,
        border=ft.border.all(1, BORDER),
        expand=True,
    )

# ── Main App ──────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title        = "Truck Cargo MS"
    page.bgcolor      = BG
    page.padding      = 0
    page.fonts        = {"Inter": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2"}
    page.theme        = ft.Theme(font_family="Inter")
    page.window_width  = 1280
    page.window_height = 800

    # ── State ─────────────────────────────────────────────────────────────────
    cargos      = []
    trucks      = []
    logs        = []
    active_tab  = ft.Ref[str]()
    active_tab.current = "dashboard"

    # ── Refs for dynamic UI ───────────────────────────────────────────────────
    stats_row       = ft.Ref[ft.Row]()
    cargo_list      = ft.Ref[ft.Column]()
    truck_list      = ft.Ref[ft.Column]()
    log_list        = ft.Ref[ft.Column]()
    content_area    = ft.Ref[ft.Column]()
    toast_bar       = ft.Ref[ft.Container]()
    nav_indicators  = {}

    # ── Toast notification ────────────────────────────────────────────────────
    def show_toast(msg: str, color=SUCCESS):
        toast_bar.current.content = ft.Row([
            ft.Icon(ft.icons.CHECK_CIRCLE_ROUNDED, color=color, size=16),
            ft.Text(msg, color=TEXT, size=13),
        ], spacing=8)
        toast_bar.current.bgcolor  = f"{color}22"
        toast_bar.current.visible  = True
        page.update()
        async def hide():
            await asyncio.sleep(3)
            toast_bar.current.visible = False
            page.update()
        page.run_task(hide)

    def add_log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        logs.insert(0, f"[{ts}]  {msg}")
        if len(logs) > 50:
            logs.pop()
        if log_list.current:
            log_list.current.controls = [
                ft.Text(l, size=11, color=MUTED, font_family="monospace") for l in logs[:20]
            ]
            page.update()

    # ── API helpers ───────────────────────────────────────────────────────────
    async def fetch_cargos():
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{API}/cargos")
                return r.json()
        except Exception as e:
            add_log(f"ERROR fetching cargos: {e}")
            return []

    async def fetch_trucks():
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{API}/trucks")
                return r.json()
        except Exception as e:
            add_log(f"ERROR fetching trucks: {e}")
            return []

    async def post_cargo(description, weight, truck_id=None):
        payload = {"description": description, "weight_kg": float(weight)}
        if truck_id:
            payload["truck_id"] = truck_id
        try:
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{API}/cargos", json=payload)
                return r.json()
        except Exception as e:
            add_log(f"ERROR creating cargo: {e}")

    async def post_truck(plate, driver, capacity):
        payload = {"plate": plate, "driver_name": driver, "capacity_kg": float(capacity)}
        try:
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{API}/trucks", json=payload)
                return r.json()
        except Exception as e:
            add_log(f"ERROR creating truck: {e}")

    async def patch_cargo(cargo_id, status):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.patch(f"{API}/cargos/{cargo_id}", json={"status": status})
                return r.json()
        except Exception as e:
            add_log(f"ERROR updating cargo: {e}")

    # ── Build cargo row ───────────────────────────────────────────────────────
    def cargo_row(c) -> ft.Container:
        color = STATUS_COLOR.get(c["status"], MUTED)
        icon  = STATUS_ICON.get(c["status"], ft.icons.HELP_OUTLINE)
        cid   = c["id"]

        def on_status_change(e, cid=cid):
            async def do():
                result = await patch_cargo(cid, e.control.value)
                if result:
                    show_toast(f"Status updated → {e.control.value}")
                    add_log(f"Cargo {cid[:8]}... → {e.control.value}")
                    await refresh_all()
            page.run_task(do)

        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=18),
                ft.Column([
                    ft.Text(c["description"], size=13, weight=ft.FontWeight.W_500, color=TEXT),
                    ft.Text(f"{c['weight_kg']} kg  ·  {c.get('created_at','')[:10]}", size=11, color=MUTED),
                ], spacing=2, expand=True),
                badge(c["status"], color),
                ft.Dropdown(
                    value=c["status"],
                    options=[ft.dropdown.Option(s) for s in ["pending","in_transit","delivered","failed"]],
                    width=130, height=36,
                    text_size=12,
                    color=TEXT,
                    bgcolor=SURFACE,
                    border_color=BORDER,
                    on_change=on_status_change,
                ),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BORDER),
            margin=ft.margin.only(bottom=6),
        )

    # ── Build truck row ───────────────────────────────────────────────────────
    def truck_row(t) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.LOCAL_SHIPPING_ROUNDED, color=ACCENT, size=20),
                ft.Column([
                    ft.Text(t["plate"], size=13, weight=ft.FontWeight.W_600, color=TEXT),
                    ft.Text(f"Driver: {t.get('driver_name','—')}  ·  Capacity: {t.get('capacity_kg','—')} kg",
                            size=11, color=MUTED),
                ], spacing=2, expand=True),
                badge("active", SUCCESS),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BORDER),
            margin=ft.margin.only(bottom=6),
        )

    # ── Stats row builder ─────────────────────────────────────────────────────
    def build_stats(cargo_data, truck_data):
        total     = len(cargo_data)
        transit   = sum(1 for c in cargo_data if c["status"] == "in_transit")
        delivered = sum(1 for c in cargo_data if c["status"] == "delivered")
        failed    = sum(1 for c in cargo_data if c["status"] == "failed")
        return [
            stat_card("Total Cargos",   total,     ft.icons.INVENTORY_2_ROUNDED,     ACCENT),
            stat_card("In Transit",     transit,   ft.icons.LOCAL_SHIPPING_ROUNDED,  INFO),
            stat_card("Delivered",      delivered, ft.icons.CHECK_CIRCLE_ROUNDED,    SUCCESS),
            stat_card("Failed",         failed,    ft.icons.ERROR_ROUNDED,           DANGER),
        ]

    # ── Add cargo dialog ──────────────────────────────────────────────────────
    def open_add_cargo(e):
        desc   = ft.TextField(label="Description", bgcolor=SURFACE, color=TEXT,
                               border_color=BORDER, label_style=ft.TextStyle(color=MUTED))
        weight = ft.TextField(label="Weight (kg)", bgcolor=SURFACE, color=TEXT,
                               border_color=BORDER, label_style=ft.TextStyle(color=MUTED), keyboard_type=ft.KeyboardType.NUMBER)

        def submit(e):
            async def do():
                if desc.value and weight.value:
                    result = await post_cargo(desc.value, weight.value)
                    if result:
                        show_toast(f"Cargo '{desc.value}' created!")
                        add_log(f"New cargo: {desc.value} ({weight.value}kg)")
                        page.close(dlg)
                        await refresh_all()
            page.run_task(do)

        dlg = ft.AlertDialog(
            title=ft.Text("Add Cargo", color=TEXT, weight=ft.FontWeight.W_600),
            bgcolor=CARD,
            content=ft.Column([desc, weight], spacing=12, width=340),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dlg),
                              style=ft.ButtonStyle(color=MUTED)),
                ft.ElevatedButton("Create", bgcolor=ACCENT, color="#000",
                                  on_click=submit),
            ],
        )
        page.open(dlg)

    # ── Add truck dialog ──────────────────────────────────────────────────────
    def open_add_truck(e):
        plate    = ft.TextField(label="Plate Number", bgcolor=SURFACE, color=TEXT,
                                 border_color=BORDER, label_style=ft.TextStyle(color=MUTED))
        driver   = ft.TextField(label="Driver Name", bgcolor=SURFACE, color=TEXT,
                                 border_color=BORDER, label_style=ft.TextStyle(color=MUTED))
        capacity = ft.TextField(label="Capacity (kg)", bgcolor=SURFACE, color=TEXT,
                                 border_color=BORDER, label_style=ft.TextStyle(color=MUTED),
                                 keyboard_type=ft.KeyboardType.NUMBER)

        def submit(e):
            async def do():
                if plate.value and driver.value and capacity.value:
                    result = await post_truck(plate.value, driver.value, capacity.value)
                    if result:
                        show_toast(f"Truck '{plate.value}' added!")
                        add_log(f"New truck: {plate.value} — {driver.value}")
                        page.close(dlg)
                        await refresh_all()
            page.run_task(do)

        dlg = ft.AlertDialog(
            title=ft.Text("Add Truck", color=TEXT, weight=ft.FontWeight.W_600),
            bgcolor=CARD,
            content=ft.Column([plate, driver, capacity], spacing=12, width=340),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dlg),
                              style=ft.ButtonStyle(color=MUTED)),
                ft.ElevatedButton("Add Truck", bgcolor=ACCENT, color="#000",
                                  on_click=submit),
            ],
        )
        page.open(dlg)

    # ── Refresh all data ──────────────────────────────────────────────────────
    async def refresh_all():
        nonlocal cargos, trucks
        cargos = await fetch_cargos()
        trucks = await fetch_trucks()

        if stats_row.current:
            stats_row.current.controls = build_stats(cargos, trucks)

        if cargo_list.current:
            cargo_list.current.controls = (
                [cargo_row(c) for c in cargos] if cargos
                else [ft.Text("No cargos yet. Add one!", color=MUTED, size=13)]
            )

        if truck_list.current:
            truck_list.current.controls = (
                [truck_row(t) for t in trucks] if trucks
                else [ft.Text("No trucks yet. Add one!", color=MUTED, size=13)]
            )

        page.update()

    # ── WebSocket listener ────────────────────────────────────────────────────
    async def ws_listener():
        while True:
            try:
                async with websockets.connect(WS) as ws:
                    add_log("WebSocket connected")
                    async for msg in ws:
                        data = json.loads(msg)
                        add_log(f"WS event: {data}")
                        await refresh_all()
            except Exception as e:
                add_log(f"WS disconnected, retrying... ({e})")
                await asyncio.sleep(3)

    # ── Navigation ────────────────────────────────────────────────────────────
    def nav_item(label, icon, tab_id) -> ft.Container:
        is_active = active_tab.current == tab_id
        indicator = ft.Container(width=3, height=20, bgcolor=ACCENT if is_active else "transparent",
                                  border_radius=2)
        row = ft.Container(
            ref=None,
            content=ft.Row([
                indicator,
                ft.Icon(icon, color=TEXT if is_active else MUTED, size=17),
                ft.Text(label, size=13, color=TEXT if is_active else MUTED,
                        weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400),
            ], spacing=10),
            bgcolor=f"{ACCENT}18" if is_active else "transparent",
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            on_click=lambda e, t=tab_id: switch_tab(t),
            on_hover=lambda e: setattr(e.control, 'bgcolor',
                                       f"{ACCENT}18" if e.data == "true" else
                                       (f"{ACCENT}18" if active_tab.current == tab_id else "transparent"))
                     or page.update(),
            animate=ft.animation.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
        nav_indicators[tab_id] = row
        return row

    def switch_tab(tab_id: str):
        active_tab.current = tab_id
        content_area.current.controls = build_tab(tab_id)
        page.update()
        page.run_task(refresh_all)

    # ── Tab content builders ──────────────────────────────────────────────────
    def build_dashboard():
        return [
            ft.Row([
                ft.Text("Dashboard", size=22, weight=ft.FontWeight.W_700, color=TEXT),
                ft.Container(expand=True),
                ft.ElevatedButton("+ Add Cargo", bgcolor=ACCENT, color="#000",
                                   on_click=open_add_cargo,
                                   style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ]),
            ft.Text("Overview of your cargo operations", size=13, color=MUTED),
            ft.Container(height=16),
            ft.Row(ref=stats_row, controls=build_stats(cargos, trucks), spacing=12),
            ft.Container(height=20),
            section_title("Recent Cargos", ft.icons.INVENTORY_2_ROUNDED),
            ft.Container(height=8),
            ft.Column(
                ref=cargo_list,
                controls=[cargo_row(c) for c in cargos] if cargos
                          else [ft.Text("No cargos yet.", color=MUTED, size=13)],
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
            ),
        ]

    def build_cargos():
        return [
            ft.Row([
                ft.Text("Cargos", size=22, weight=ft.FontWeight.W_700, color=TEXT),
                ft.Container(expand=True),
                ft.ElevatedButton("+ Add Cargo", bgcolor=ACCENT, color="#000",
                                   on_click=open_add_cargo,
                                   style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ]),
            ft.Text("Manage and track all cargo shipments", size=13, color=MUTED),
            ft.Container(height=16),
            ft.Column(
                ref=cargo_list,
                controls=[cargo_row(c) for c in cargos] if cargos
                          else [ft.Text("No cargos yet.", color=MUTED, size=13)],
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
                expand=True,
            ),
        ]

    def build_trucks():
        return [
            ft.Row([
                ft.Text("Trucks", size=22, weight=ft.FontWeight.W_700, color=TEXT),
                ft.Container(expand=True),
                ft.ElevatedButton("+ Add Truck", bgcolor=ACCENT, color="#000",
                                   on_click=open_add_truck,
                                   style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ]),
            ft.Text("Manage your fleet of trucks", size=13, color=MUTED),
            ft.Container(height=16),
            ft.Column(
                ref=truck_list,
                controls=[truck_row(t) for t in trucks] if trucks
                          else [ft.Text("No trucks yet.", color=MUTED, size=13)],
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
                expand=True,
            ),
        ]

    def build_logs():
        return [
            ft.Text("Event Logs", size=22, weight=ft.FontWeight.W_700, color=TEXT),
            ft.Text("Real-time system events from DB triggers, workers, and WebSocket", size=13, color=MUTED),
            ft.Container(height=16),
            ft.Container(
                content=ft.Column(
                    ref=log_list,
                    controls=[ft.Text(l, size=11, color=MUTED, font_family="monospace") for l in logs[:20]]
                              if logs else [ft.Text("No events yet. Start interacting!", color=MUTED, size=13)],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=4,
                ),
                bgcolor=SURFACE,
                border_radius=10,
                padding=16,
                border=ft.border.all(1, BORDER),
                expand=True,
            ),
        ]

    def build_tab(tab_id: str):
        return {
            "dashboard": build_dashboard,
            "cargos":    build_cargos,
            "trucks":    build_trucks,
            "logs":      build_logs,
        }.get(tab_id, build_dashboard)()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    sidebar = ft.Container(
        width=220,
        bgcolor=SURFACE,
        border=ft.border.only(right=ft.BorderSide(1, BORDER)),
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.LOCAL_SHIPPING_ROUNDED, color=ACCENT, size=22),
                    ft.Text("CargoMS", size=16, weight=ft.FontWeight.W_700, color=TEXT),
                ], spacing=8),
                padding=ft.padding.fromLTRB(16, 20, 16, 20),
            ),
            divider(),
            ft.Container(height=8),
            ft.Container(
                content=ft.Column([
                    ft.Text("MAIN", size=10, color=MUTED, weight=ft.FontWeight.W_600,
                            letter_spacing=1.2),
                    ft.Container(height=4),
                    nav_item("Dashboard", ft.icons.DASHBOARD_ROUNDED,       "dashboard"),
                    nav_item("Cargos",    ft.icons.INVENTORY_2_ROUNDED,     "cargos"),
                    nav_item("Trucks",    ft.icons.LOCAL_SHIPPING_ROUNDED,  "trucks"),
                    ft.Container(height=12),
                    ft.Text("SYSTEM", size=10, color=MUTED, weight=ft.FontWeight.W_600,
                            letter_spacing=1.2),
                    ft.Container(height=4),
                    nav_item("Event Logs", ft.icons.TERMINAL_ROUNDED, "logs"),
                ], spacing=2),
                padding=ft.padding.symmetric(horizontal=12),
            ),
            ft.Container(expand=True),
            divider(),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CIRCLE, color=SUCCESS, size=8),
                    ft.Text("API connected", size=11, color=MUTED),
                ], spacing=6),
                padding=ft.padding.fromLTRB(16, 12, 16, 16),
            ),
        ]),
    )

    # ── Toast bar ─────────────────────────────────────────────────────────────
    toast = ft.Container(
        ref=toast_bar,
        visible=False,
        bgcolor=f"{SUCCESS}22",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.border.all(1, f"{SUCCESS}55"),
        margin=ft.margin.only(bottom=12),
    )

    # ── Main content area ─────────────────────────────────────────────────────
    main_area = ft.Container(
        expand=True,
        bgcolor=BG,
        content=ft.Column([
            toast,
            ft.Column(
                ref=content_area,
                controls=build_tab("dashboard"),
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=8,
            ),
        ], spacing=0, expand=True),
        padding=ft.padding.fromLTRB(32, 28, 32, 20),
    )

    # ── Page layout ───────────────────────────────────────────────────────────
    page.add(
        ft.Row([sidebar, main_area], expand=True, spacing=0)
    )

    # ── Initial load ──────────────────────────────────────────────────────────
    async def on_start():
        await refresh_all()
        page.run_task(ws_listener)

    page.run_task(on_start)


ft.app(target=main)