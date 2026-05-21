import streamlit as st
from datetime import datetime
import io
from decimal import Decimal, ROUND_HALF_UP
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, green

# Configurar la página para móvil
st.set_page_config(
    page_title="Facturación Simple",
    page_icon="📄",
    layout="centered"
)

# ============================================================================
# FUNCIONES DE REDONDEO (CORRECTAS PARA HACIENDA)
# ============================================================================

def redondear_euros(cantidad):
    """
    Redondeo al céntimo más cercano según normativa española.
    Usa ROUND_HALF_UP: 11.085 → 11.09, 11.084 → 11.08
    """
    if isinstance(cantidad, float):
        # Convertir float a string con precisión controlada
        cantidad = str(round(cantidad, 10))
    
    d = Decimal(cantidad)
    return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def eur(cantidad):
    """Formatea una cantidad como moneda Euro con redondeo correcto"""
    return f"{redondear_euros(cantidad):.2f} €"


def parse_number(texto):
    """Convierte texto a número, manejando comas como decimales"""
    try:
        return float(str(texto).replace(',', '.'))
    except ValueError:
        return 0.0


def calcular_con_redondeo(precio, iva, incluye_iva):
    """
    Calcula base imponible, cuota de IVA y precio con IVA
    Aplicando redondeo correcto después de CADA operación
    """
    if incluye_iva:
        # Precio ya incluye IVA: calculamos base imponible
        base = redondear_euros(precio / (1 + iva / 100))
        cuota_iva = redondear_euros(precio - base)
        precio_con_iva = redondear_euros(precio)
    else:
        # Precio sin IVA: calculamos IVA y total
        base = redondear_euros(precio)
        cuota_iva = redondear_euros(precio * iva / 100)
        precio_con_iva = redondear_euros(base + cuota_iva)
    
    return base, cuota_iva, precio_con_iva


# ============================================================================
# FUNCIONES PARA EL PDF
# ============================================================================

def wrap_text(c, text, x, y, width_mm=120, font_name="Helvetica", font_size=10):
    """Envuelve texto en múltiples líneas y devuelve la nueva posición Y"""
    c.setFont(font_name, font_size)
    width_pts = width_mm * mm
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if c.stringWidth(test_line, font_name, font_size) <= width_pts:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    for line in lines:
        c.drawString(x, y, line)
        y -= 4 * mm
    
    return y


def generar_pdf_factura(emisor, datos_factura):
    """Genera el PDF de la factura y devuelve los bytes del PDF"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    MARGIN_X = 25 * mm
    TOP = height - 25 * mm
    
    # Asegurar que todos los totales están redondeados
    base_imponible = redondear_euros(datos_factura['base_imponible'])
    iva_total = redondear_euros(datos_factura['iva'])
    total = redondear_euros(datos_factura['total'])
    
    # Encabezado
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN_X, TOP, "FACTURA")
    
    if datos_factura.get('pagada', False):
        c.setFillColor(green)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(width - MARGIN_X, TOP, "PAGADO")
        c.setFillColor(black)
    
    # Datos emisor
    y = TOP - 12 * mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Emisor: {emisor['nombre']}")
    y -= 5 * mm
    c.drawString(MARGIN_X, y, f"NIF: {emisor['NIF']}")
    y -= 5 * mm
    c.drawString(MARGIN_X, y, f"Dirección: {emisor['direccion']}")
    y -= 5 * mm
    c.drawString(MARGIN_X, y, f"Email: {emisor['email']}")
    
    # Datos factura
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Datos de la factura")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Factura nº: {datos_factura['numero']}")
    y -= 5 * mm
    c.drawString(MARGIN_X, y, f"Fecha de emisión: {datos_factura['fecha_emision']}")
    
    # Datos cliente
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Cliente")
    
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Nombre: {datos_factura['cliente']}")
    
    y -= 5 * mm
    c.drawString(MARGIN_X, y, f"NIF: {datos_factura['nif_cliente']}")
    
    y -= 5 * mm
    y = wrap_text(
        c,
        f"Dirección: {datos_factura['direccion_cliente']}",
        MARGIN_X,
        y,
        width_mm=120
    )
    
    # Conceptos
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Conceptos")
    y -= 6 * mm
    
    c.setFont("Helvetica-Bold", 9)
    col1_x = MARGIN_X
    col2_x = MARGIN_X + 80 * mm
    col3_x = MARGIN_X + 110 * mm
    col4_x = MARGIN_X + 130 * mm
    
    c.drawString(col1_x, y, "CONCEPTO")
    c.drawString(col2_x, y, "PRECIO SIN IVA")
    c.drawString(col3_x, y, "TIPO IVA")
    c.drawString(col4_x, y, "PRECIO CON IVA")
    
    y -= 4 * mm
    c.line(MARGIN_X, y, width - MARGIN_X, y)
    y -= 4 * mm
    
    c.setFont("Helvetica", 9)
    for idx, concepto in enumerate(datos_factura['conceptos']):
        original_y = y
        
        y = wrap_text(
            c,
            concepto['descripcion'],
            col1_x,
            y,
            width_mm=75,
            font_name="Helvetica",
            font_size=9
        )
        
        c.drawString(col2_x, original_y, eur(concepto['base']))
        c.drawString(col3_x, original_y, f"{concepto['iva']:.1f}%")
        c.drawString(col4_x, original_y, eur(concepto['precio_con_iva']))
        
        y -= 2 * mm
        if idx < len(datos_factura['conceptos']) - 1:
            c.line(MARGIN_X, y, width - MARGIN_X, y)
            y -= 4 * mm
        else:
            y -= 2 * mm
    
    # Totales
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Importes")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Base imponible: {eur(base_imponible)}")
    y -= 5 * mm
    c.drawString(MARGIN_X, y, f"IVA total: {eur(iva_total)}")
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, f"TOTAL: {eur(total)}")
    
    # Pie
    y -= 12 * mm
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN_X, y, "Factura")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer


# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================

# Cargar datos del emisor desde secrets
try:
    EMISOR = {
        'nombre': st.secrets["emisor"]["nombre"],
        'NIF': st.secrets["emisor"]["nif"],
        'direccion': st.secrets["emisor"]["direccion"],
        'email': st.secrets["emisor"]["email"]
    }
except Exception as e:
    st.error(f"Error cargando configuración: {e}")
    st.stop()

# Inicializar estado de sesión
if 'conceptos' not in st.session_state:
    st.session_state.conceptos = []


# ============================================================================
# INTERFAZ DE USUARIO
# ============================================================================

st.title("📄 Generador de Facturas")
st.markdown("---")

# Selección de tipo de factura
tipo_factura = st.radio(
    "Tipo de factura:",
    ["Simplificada", "Completa"],
    help="Factura simplificada (ticket) o factura completa con todos los datos"
)

st.markdown("---")

# Datos de la factura
col1, col2 = st.columns(2)
with col1:
    numero_factura = st.text_input(
        "Número y serie de factura *",
        help="Ej: 2024/001",
        key="num_factura"
    )
with col2:
    fecha_emision = st.date_input(
        "Fecha de emisión",
        value=datetime.now(),
        format="DD/MM/YYYY"
    )

# Datos del cliente
st.subheader("Datos del cliente")

if tipo_factura == "Completa":
    cliente = st.text_input("Nombre del cliente *", key="cliente_nombre")
    nif_cliente = st.text_input("NIF del cliente *", key="cliente_nif")
    direccion_cliente = st.text_area("Dirección del cliente *", key="cliente_direccion")
else:
    cliente = st.text_input(
        "Nombre del cliente (opcional)",
        help="Para factura simplificada puede dejarse vacío",
        key="cliente_nombre"
    )
    nif_cliente = st.text_input("NIF del cliente (opcional)", key="cliente_nif")
    direccion_cliente = st.text_area("Dirección del cliente (opcional)", key="cliente_direccion")

# Estado de pago
pagada = st.checkbox("¿Factura pagada?", value=False)

st.markdown("---")

# Gestión de conceptos
st.subheader("📝 Conceptos")

with st.form("añadir_concepto"):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        descripcion = st.text_input("Descripción", key="desc_input")
    with col2:
        precio = st.number_input(
            "Precio (€)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            key="precio_input"
        )
    with col3:
        iva = st.number_input(
            "IVA (%)",
            min_value=0.0,
            max_value=100.0,
            value=21.0,
            step=1.0,
            key="iva_input"
        )
    
    incluye_iva = st.checkbox("El precio YA incluye el IVA", value=False, key="incluye_iva")
    
    submitted = st.form_submit_button("➕ Añadir concepto")
    if submitted:
        if descripcion and precio > 0:
            # Usar la función de cálculo con redondeo correcto
            base, cuota_iva, precio_con_iva = calcular_con_redondeo(precio, iva, incluye_iva)
            
            st.session_state.conceptos.append({
                "descripcion": descripcion,
                "precio": redondear_euros(precio),
                "iva": iva,
                "incluye_iva": incluye_iva,
                "base": base,
                "cuota_iva": cuota_iva,
                "precio_con_iva": precio_con_iva
            })
            st.success(f"✓ Añadido: {descripcion}")
            st.rerun()
        else:
            st.error("❌ Descripción y precio son obligatorios")

# Mostrar conceptos añadidos
if st.session_state.conceptos:
    st.subheader("📋 Conceptos añadidos:")
    
    # Calcular totales CON REDONDEO después de cada suma
    base_imponible = redondear_euros(sum(c['base'] for c in st.session_state.conceptos))
    cuota_iva_total = redondear_euros(sum(c['cuota_iva'] for c in st.session_state.conceptos))
    total = redondear_euros(base_imponible + cuota_iva_total)
    
    # Tabla de conceptos
    for idx, concepto in enumerate(st.session_state.conceptos):
        cols = st.columns([3, 1.5, 1, 1.5, 0.5])
        with cols[0]:
            st.write(concepto['descripcion'])
        with cols[1]:
            st.write(eur(concepto['base']))
        with cols[2]:
            st.write(f"{concepto['iva']:.0f}%")
        with cols[3]:
            st.write(eur(concepto['precio_con_iva']))
        with cols[4]:
            if st.button("🗑️", key=f"del_{idx}"):
                st.session_state.conceptos.pop(idx)
                st.rerun()
    
    st.markdown("---")
    
    # Totales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base imponible", eur(base_imponible))
    with col2:
        st.metric("IVA total", eur(cuota_iva_total))
    with col3:
        st.metric("TOTAL", eur(total))
    
    # Verificación de consistencia (base + iva debe = total)
    suma_verificacion = redondear_euros(base_imponible + cuota_iva_total)
    if suma_verificacion != total:
        st.warning(f"⚠️ Nota: Verificación de redondeo - Base+IVA={eur(suma_verificacion)} vs Total={eur(total)}")
    
    st.markdown("---")
    
    # Botón para generar factura
    if st.button("📄 Generar Factura", type="primary", use_container_width=True):
        # Validaciones
        error = False
        if not numero_factura:
            st.error("❌ El número de factura es obligatorio")
            error = True
        elif tipo_factura == "Completa" and (not cliente or not nif_cliente or not direccion_cliente):
            st.error("❌ Para factura completa, todos los datos del cliente son obligatorios")
            error = True
        elif not st.session_state.conceptos:
            st.error("❌ Debe añadir al menos un concepto")
            error = True
        
        if not error:
            # Preparar datos (todo redondeado)
            datos_factura = {
                "numero": numero_factura,
                "fecha_emision": fecha_emision.strftime("%d/%m/%Y"),
                "cliente": cliente if cliente else "Cliente no especificado",
                "nif_cliente": nif_cliente if nif_cliente else "No especificado",
                "direccion_cliente": direccion_cliente if direccion_cliente else "No especificada",
                "pagada": pagada,
                "base_imponible": base_imponible,
                "iva": cuota_iva_total,
                "total": total,
                "conceptos": st.session_state.conceptos
            }
            
            try:
                # Generar PDF en memoria
                pdf_buffer = generar_pdf_factura(EMISOR, datos_factura)
                
                st.success("✅ ¡Factura generada correctamente!")
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar Factura PDF",
                    data=pdf_buffer,
                    file_name=f"factura_{numero_factura.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Mostrar información de pago si no está pagada
                if not pagada:
                    st.info("💡 **Información de pago:**")
                    st.markdown(f"""
                    - **Método:** Transferencia bancaria / Efectivo
                    - **Referencia:** {numero_factura}
                    - **Total a pagar:** {eur(total)}
                    """)
                    
                    st.warning("⚠️ Esta factura NO está marcada como pagada")
                
            except Exception as e:
                st.error(f"❌ Error al generar la factura: {str(e)}")
else:
    st.info("➕ Añade al menos un concepto para generar la factura")

# Botón para limpiar
if st.button("🔄 Limpiar todos los conceptos", use_container_width=True):
    st.session_state.conceptos = []
    st.rerun()

# Footer
st.markdown("---")
st.caption(f"Emisor: {EMISOR['nombre']} - {EMISOR['NIF']}")
