# Sistema Web de Gestión de Pedidos, Expedientes e Insumos — Sierra Diseños y Bordados (MVP)

Aplicación web construida en **Python 3 + Flask + SQLite + Bootstrap 5** con una arquitectura organizada en **`models/`**, **`services/`**, **`controllers/`** y **`templates/`**, alineada con el método **ADM de TOGAF** para la mipyme **Sierra Diseños y Bordados** (Santa Marta D.T.C.H., Magdalena — NIT 77166736-5).

---

## 1. Estructura del Proyecto (`models`, `services`, `controllers`, `templates`)

```text
proyecto_inventario_Mipyme/
├── app.py                              # Punto de entrada principal (create_app + handler 413)
├── config.py                           # Clase Config (Carga .env, BD, uploads y constantes)
├── models/                             # Modelos de Datos y Persistencia SQL (POO)
│   ├── __init__.py
│   ├── database.py                     # Clase Database (Conexión SQLite, 4 tablas y semilla)
│   ├── usuario.py                      # Clase Usuario (Tabla usuarios)
│   ├── cliente.py                      # Clase Cliente (Tabla clientes indexada por Cédula/NIT)
│   ├── pedido.py                       # Clase Pedido (Tabla pedidos, bocetos y estados)
│   └── insumo.py                       # Clase Insumo (Tabla insumos y semáforo de stock mínimo)
├── services/                           # Lógica de Negocio
│   ├── __init__.py
│   ├── auth_service.py                 # Clase AuthService (Login, Hash y Roles RBAC)
│   ├── pedido_service.py               # Clase PedidoService (Pedidos, bocetos, cédula y WhatsApp)
│   └── inventario_service.py           # Clase InventarioService (Stock de hilos/interlón, analítica y CSV)
├── controllers/                        # Controladores de Rutas Web y API REST
│   ├── __init__.py
│   ├── auth_controller.py              # Clase AuthController (/login, /logout + decoradores RBAC)
│   ├── pedido_controller.py            # Clase PedidoController (/, /pedidos/*, /tv, /clientes, /cotizar)
│   ├── inventario_controller.py        # Clase InventarioController (/insumos, /insumos/*, /backup/csv)
│   └── api_controller.py               # Clase ApiController (/api/pedidos, /api/insumos, /api/clientes/<cedula>)
├── static/uploads/                     # Imágenes y PDFs de referencia subidos por clientes
└── templates/                          # Vistas HTML5 + Bootstrap 5
```

---

## 2. Credenciales de Prueba (RBAC)

| Rol | Usuario | Contraseña | Permisos |
| :--- | :--- | :--- | :--- |
| **Administrador (Recepción / Dueño)** | `admin` | `admin123` | Acceso total: cuaderno de pedidos, edición y asignación de hilos, inventario de hilos, directorio de clientes y backups CSV. |
| **Operario de Planta (Bordadoras)** | `operario` | `operario123` | Consulta de órdenes, **Pantalla TV** con códigos exactos de hilo, bocetos de referencia y cambio de estado a *En Proceso* / *Listo*. |
| **Cliente (Acceso público en `/cotizar`)** | *Sin clave* | *Sin clave* | Envío de idea + imagen/PDF de referencia hacia WhatsApp, selección de colores del inventario y consulta de pedido por Cédula/NIT. |

---

## 3. Ejecución Local

```bash
pip install -r requirements.txt
python app.py
```

Abrir en el navegador:
* **Vista del Cliente:** `http://127.0.0.1:5000/cotizar`
* **Ingreso del Taller:** `http://127.0.0.1:5000/login`
