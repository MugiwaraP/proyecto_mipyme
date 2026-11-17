import os
import sqlite3
from flask import g
from werkzeug.security import generate_password_hash
from config import Config


class Database:
    """Clase encargada de la conexión a la base de datos SQLite/PostgreSQL y creación de tablas."""

    def __init__(self, db_path: str = Config.SQLITE_PATH):
        self.db_path = db_path
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        if "db" not in g:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
        return g.db

    @staticmethod
    def close_connection(exception=None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db(self) -> None:
        """Crea las tablas relacionales (usuarios, clientes, pedidos, insumos, historial_pedidos) y datos semilla."""
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        cur = db.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL CHECK(rol IN ('admin', 'operario'))
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL,
                direccion TEXT DEFAULT '',
                hilos_corporativos TEXT DEFAULT '',
                acepta_ley1581 INTEGER DEFAULT 1,
                fecha_registro TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                tipo_servicio TEXT NOT NULL,
                descripcion_y_hilos TEXT NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                modalidad_entrega TEXT NOT NULL DEFAULT 'Local',
                soporte_fiscal TEXT NOT NULL DEFAULT 'Recibo de Caja',
                estado TEXT NOT NULL CHECK(estado IN ('Cotización', 'Pendiente', 'En Proceso', 'Listo', 'Entregado')),
                fecha_creacion TEXT NOT NULL,
                imagen_url TEXT DEFAULT '',
                solicitud_original TEXT DEFAULT '',
                acuerdo_whatsapp TEXT DEFAULT '',
                evidencia_url TEXT DEFAULT '',
                confirmado_por TEXT DEFAULT '',
                fecha_confirmacion TEXT DEFAULT '',
                FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
            )
            """
        )

        # Migración ligera por si la BD existía antes sin columnas de respaldo/pruebas
        cols_pedidos = {
            r["name"] for r in cur.execute("PRAGMA table_info(pedidos)").fetchall()
        }
        nuevas_cols = [
            ("imagen_url", "TEXT DEFAULT ''"),
            ("solicitud_original", "TEXT DEFAULT ''"),
            ("acuerdo_whatsapp", "TEXT DEFAULT ''"),
            ("evidencia_url", "TEXT DEFAULT ''"),
            ("confirmado_por", "TEXT DEFAULT ''"),
            ("fecha_confirmacion", "TEXT DEFAULT ''"),
        ]
        for col_name, col_def in nuevas_cols:
            if col_name not in cols_pedidos:
                cur.execute(f"ALTER TABLE pedidos ADD COLUMN {col_name} {col_def}")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS historial_pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                fecha_hora TEXT NOT NULL,
                autor TEXT NOT NULL,
                accion TEXT NOT NULL,
                resumen TEXT NOT NULL,
                archivo_url TEXT DEFAULT '',
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS insumos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_referencia TEXT UNIQUE,
                nombre_color TEXT NOT NULL,
                color_hex TEXT NOT NULL DEFAULT '#1e293b',
                categoria TEXT NOT NULL CHECK(categoria IN ('Hilo', 'Interlon', 'Insumo')),
                stock_actual INTEGER NOT NULL CHECK(stock_actual >= 0),
                stock_minimo INTEGER NOT NULL CHECK(stock_minimo >= 0),
                unidad TEXT NOT NULL DEFAULT 'Conos'
            )
            """
        )

        # Migración ligera para permitir materiales sin código obligatorio (codigo_referencia NULL)
        cols_insumos = cur.execute("PRAGMA table_info(insumos)").fetchall()
        for col in cols_insumos:
            if col["name"] == "codigo_referencia" and col["notnull"] == 1:
                cur.execute(
                    """
                    CREATE TABLE insumos_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo_referencia TEXT UNIQUE,
                        nombre_color TEXT NOT NULL,
                        color_hex TEXT NOT NULL DEFAULT '#1e293b',
                        categoria TEXT NOT NULL CHECK(categoria IN ('Hilo', 'Interlon', 'Insumo')),
                        stock_actual INTEGER NOT NULL CHECK(stock_actual >= 0),
                        stock_minimo INTEGER NOT NULL CHECK(stock_minimo >= 0),
                        unidad TEXT NOT NULL DEFAULT 'Conos'
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO insumos_new
                    (id, codigo_referencia, nombre_color, color_hex, categoria, stock_actual, stock_minimo, unidad)
                    SELECT id, NULLIF(TRIM(codigo_referencia), ''), nombre_color, color_hex, categoria, stock_actual, stock_minimo, unidad
                    FROM insumos
                    """
                )
                cur.execute("DROP TABLE insumos")
                cur.execute("ALTER TABLE insumos_new RENAME TO insumos")
                break

        self._seed_data(cur)
        self._backfill_respaldo_pedidos(cur)
        db.commit()
        db.close()

    @staticmethod
    def _seed_data(cur: sqlite3.Cursor) -> None:
        cur.execute("SELECT COUNT(*) as total FROM usuarios")
        if cur.fetchone()["total"] == 0:
            cur.executemany(
                "INSERT INTO usuarios (nombre, username, password_hash, rol) VALUES (?, ?, ?, ?)",
                [
                    (
                        "Roberto Sierra / Administradora",
                        "admin",
                        generate_password_hash("admin123"),
                        "admin",
                    ),
                    (
                        "José (Operario Bordadoras)",
                        "operario",
                        generate_password_hash("operario123"),
                        "operario",
                    ),
                ],
            )

        # Catálogo amplio de 20 conos de hilo codificados + interlón e insumos
        insumos_catalogo = [
            ("HILO-3314", "Marrón Café Oscuro", "#4A2C11", "Hilo", 2, 4, "Conos"),
            ("HILO-3318", "Marrón Tabaco Medio", "#8B5A2B", "Hilo", 6, 3, "Conos"),
            ("HILO-3305", "Beige / Arena Caqui", "#D2B48C", "Hilo", 7, 3, "Conos"),
            ("HILO-4010", "Azul Oscuro Naval", "#0F2942", "Hilo", 9, 4, "Conos"),
            ("HILO-4021", "Azul Rey Corporativo", "#1D4ED8", "Hilo", 8, 4, "Conos"),
            ("HILO-4035", "Azul Celeste / Cielo", "#38BDF8", "Hilo", 6, 3, "Conos"),
            ("HILO-4050", "Azul Turquesa Mar", "#0D9488", "Hilo", 5, 2, "Conos"),
            ("HILO-1108", "Dorado Metálico", "#D97706", "Hilo", 3, 4, "Conos"),
            ("HILO-1120", "Amarillo Sol Vivo", "#FACC15", "Hilo", 7, 3, "Conos"),
            ("HILO-1510", "Naranja Industrial", "#EA580C", "Hilo", 5, 2, "Conos"),
            ("HILO-2205", "Rojo Escarlata", "#DC2626", "Hilo", 6, 3, "Conos"),
            ("HILO-2240", "Vino Tinto / Burdeos", "#7F1D1D", "Hilo", 5, 3, "Conos"),
            ("HILO-2810", "Rosado / Fucsia", "#DB2777", "Hilo", 4, 2, "Conos"),
            ("HILO-6210", "Morado / Violeta", "#7C3AED", "Hilo", 4, 2, "Conos"),
            ("HILO-5110", "Verde Esmeralda", "#059669", "Hilo", 6, 3, "Conos"),
            ("HILO-5140", "Verde Oliva / Militar", "#3F6212", "Hilo", 5, 2, "Conos"),
            ("HILO-8015", "Gris Plata Claro", "#94A3B8", "Hilo", 6, 3, "Conos"),
            ("HILO-8040", "Gris Carbón Oscuro", "#475569", "Hilo", 5, 3, "Conos"),
            ("HILO-1001", "Blanco Óptico", "#F8FAFC", "Hilo", 12, 5, "Conos"),
            ("HILO-9000", "Negro Intenso", "#0F172A", "Hilo", 10, 5, "Conos"),
            ("INT-001", "Interlón / Entretela Fija Blanca", "#E2E8F0", "Interlon", 1, 3, "Rollos"),
            ("INT-002", "Interlón Desprendible Grueso", "#CBD5E1", "Interlon", 4, 2, "Rollos"),
            ("INS-AG01", "Agujas Bordadora Industrial DBxK5", "#64748B", "Insumo", 24, 10, "Unidades"),
            ("INS-DTF1", "Tinta Estampado Textil CMYK", "#7C3AED", "Insumo", 5, 2, "Litros"),
        ]
        cur.executemany(
            """
            INSERT OR IGNORE INTO insumos
            (codigo_referencia, nombre_color, color_hex, categoria, stock_actual, stock_minimo, unidad)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            insumos_catalogo,
        )

        cur.execute("SELECT COUNT(*) as total FROM clientes")
        if cur.fetchone()["total"] == 0:
            ahora = "2026-11-16 08:30"
            cur.executemany(
                """
                INSERT INTO clientes
                (cedula, nombre, telefono, direccion, hilos_corporativos, acepta_ley1581, fecha_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "900412881-2",
                        "Hotel Tayrona Mar Boutique",
                        "3158901122",
                        "Cra 1 # 12-40 Centro Histórico, Santa Marta",
                        "Aguja 1: HILO-1108 (Dorado Metálico) | Aguja 2: HILO-4021 (Azul Rey) | Base: INT-001",
                        1,
                        ahora,
                    ),
                    (
                        "891780123-5",
                        "Colegio San Luis Beltrán",
                        "3004519988",
                        "Av. Libertador # 24-60, Santa Marta",
                        "Aguja 1: HILO-4021 (Azul Rey) | Aguja 2: HILO-1001 (Blanco) | Aguja 3: HILO-2205 (Rojo)",
                        1,
                        ahora,
                    ),
                    (
                        "901234567-8",
                        "Logística y Café de la Sierra S.A.S.",
                        "3106723344",
                        "Calle 18 # 6-20, Santa Marta",
                        "Aguja 1: HILO-3314 (Marrón Café Oscuro - NO usar 3318) | Aguja 2: HILO-1108 (Dorado)",
                        1,
                        ahora,
                    ),
                    (
                        "1082945112",
                        "Carlos Andrés Mendoza (Club Deportivo Gaira)",
                        "3127784410",
                        "Calle 11 # 15-30 Gaira, Santa Marta",
                        "Aguja 1: HILO-5110 (Verde Esmeralda) | Aguja 2: HILO-9000 (Negro)",
                        1,
                        ahora,
                    ),
                    (
                        "77166736",
                        "Dotaciones Turísticas El Rodadero",
                        "3114046465",
                        "Cra 2 # 8-15 El Rodadero, Santa Marta",
                        "Aguja 1: HILO-4021 (Azul Rey) | Aguja 2: HILO-1001 (Blanco)",
                        1,
                        ahora,
                    ),
                ],
            )

            cur.executemany(
                """
                INSERT INTO pedidos
                (cliente_id, tipo_servicio, descripcion_y_hilos, cantidad, modalidad_entrega, soporte_fiscal, estado, fecha_creacion, imagen_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        3,
                        "Solo Bordado",
                        "24 Camisas Oxford Beige — Logo pecho izq. [HILO-3314 Marrón Café Oscuro + HILO-1108 Dorado + INT-001]. ¡OJO: Usar HILO-3314, no confundir con 3318!",
                        24,
                        "Correcaminos",
                        "Factura Electrónica DIAN",
                        "En Proceso",
                        "2026-11-16 09:15",
                        "",
                    ),
                    (
                        1,
                        "Confección + Bordado/Estampado",
                        "36 Polos Piqué Blanco Recepción — Escudo Hotel en pecho y espalda [HILO-1108 Dorado + HILO-4021 Azul Rey + INT-001]",
                        36,
                        "Correcaminos",
                        "Factura Electrónica DIAN",
                        "Pendiente",
                        "2026-11-16 10:05",
                        "",
                    ),
                    (
                        2,
                        "Solo Bordado",
                        "50 Escudos Colegiales en aplique — Matriz 'SanLuis_2026.EMB' [HILO-4021 Azul Rey + HILO-1001 Blanco + HILO-2205 Rojo]",
                        50,
                        "Local",
                        "Factura Electrónica DIAN",
                        "Listo",
                        "2026-11-16 08:40",
                        "",
                    ),
                    (
                        4,
                        "Solo Estampado",
                        "18 Camisetas Deportivas — Numeración dorsal y escudo frontal [INS-DTF1]",
                        18,
                        "Local",
                        "Recibo de Caja",
                        "Pendiente",
                        "2026-11-16 11:20",
                        "",
                    ),
                    (
                        5,
                        "Confección + Bordado/Estampado",
                        "12 Gorras y 12 Toallas Playeras personalizadas — Bordado frontal 3D [HILO-4021 Azul Rey + HILO-1001 Blanco]",
                        24,
                        "Correcaminos",
                        "Factura Electrónica DIAN",
                        "Entregado",
                        "2026-11-15 16:45",
                        "",
                    ),
                ],
            )

    @staticmethod
    def _backfill_respaldo_pedidos(cur: sqlite3.Cursor) -> None:
        """Asegura que pedidos existentes o semilla tengan solicitud original e historial inicial."""
        rows = cur.execute("SELECT * FROM pedidos ORDER BY id ASC").fetchall()
        for row in rows:
            if not (row["solicitud_original"] or "").strip():
                resumen_base = (
                    f"{row['tipo_servicio']} · {row['cantidad']} prendas · "
                    f"{row['descripcion_y_hilos']} "
                    f"(Entrega: {row['modalidad_entrega']}, {row['soporte_fiscal']})"
                )
                confirmado_por = row["confirmado_por"] or ""
                fecha_conf = row["fecha_confirmacion"] or ""
                if row["estado"] != "Cotización" and not confirmado_por:
                    confirmado_por = "Roberto Sierra / Administradora"
                    fecha_conf = row["fecha_creacion"]
                cur.execute(
                    """
                    UPDATE pedidos
                    SET solicitud_original = ?,
                        confirmado_por = ?,
                        fecha_confirmacion = ?
                    WHERE id = ?
                    """,
                    (resumen_base, confirmado_por, fecha_conf, row["id"]),
                )

        cur.execute("SELECT COUNT(*) as total FROM historial_pedidos")
        if cur.fetchone()["total"] == 0:
            rows = cur.execute("SELECT * FROM pedidos ORDER BY id ASC").fetchall()
            for row in rows:
                es_cotizacion = row["estado"] == "Cotización"
                autor = "Cliente (Web)" if es_cotizacion else "Roberto Sierra / Administradora"
                accion = (
                    "Solicitud enviada por el cliente"
                    if es_cotizacion
                    else "Pedido registrado inicialmente"
                )
                cur.execute(
                    """
                    INSERT INTO historial_pedidos
                    (pedido_id, fecha_hora, autor, accion, resumen, archivo_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["fecha_creacion"],
                        autor,
                        accion,
                        row["solicitud_original"] or row["descripcion_y_hilos"],
                        row["imagen_url"] or "",
                    ),
                )
