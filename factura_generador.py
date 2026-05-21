import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, green
import json

def parse_number(texto):
    """Convierte texto a número, manejando comas como decimales"""
    try:
        return float(str(texto).replace(',', '.'))
    except ValueError:
        return 0.0

def eur(cantidad):
    """Formatea una cantidad como moneda Euro"""
    return f"{cantidad:.2f} €"

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
        y -= 4*mm
    
    return y

def generar_pdf_factura(emisor, datos_factura):
    """Genera el PDF de la factura"""
    os.makedirs("facturas", exist_ok=True)
    nombre_pdf = os.path.join("facturas", f"factura_{datos_factura['numero'].replace('/', '_')}.pdf")
    
    c = canvas.Canvas(nombre_pdf, pagesize=A4)
    width, height = A4
    
    MARGIN_X = 25 * mm
    TOP = height - 25 * mm
    
    # Encabezado
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN_X, TOP, "FACTURA")
    
    if datos_factura.get('pagada', False):
        c.setFillColor(green)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(width - MARGIN_X, TOP, "PAGADO")
        c.setFillColor(black)
    
    # Datos emisor
    y = TOP - 12*mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Emisor: {emisor['nombre']}")
    y -= 5*mm
    c.drawString(MARGIN_X, y, f"NIF: {emisor['NIF']}")
    y -= 5*mm
    c.drawString(MARGIN_X, y, f"Dirección: {emisor['direccion']}")
    y -= 5*mm
    c.drawString(MARGIN_X, y, f"Email: {emisor['email']}")
    
    # Datos factura
    y -= 8*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Datos de la factura")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Factura nº: {datos_factura['numero']}")
    y -= 5*mm
    c.drawString(MARGIN_X, y, f"Fecha de emisión: {datos_factura['fecha_emision']}")
    
    # Datos cliente
    y -= 8*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Cliente")
    
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Nombre: {datos_factura['cliente']}")
    
    y -= 5*mm
    c.drawString(MARGIN_X, y, f"NIF: {datos_factura['nif_cliente']}")
    
    y -= 5*mm
    y = wrap_text(
        c,
        f"Dirección: {datos_factura['direccion_cliente']}",
        MARGIN_X,
        y,
        width_mm=120
    )
    
    # Conceptos
    y -= 8*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Conceptos")
    y -= 6*mm
    
    c.setFont("Helvetica-Bold", 9)
    col1_x = MARGIN_X
    col2_x = MARGIN_X + 80 * mm
    col3_x = MARGIN_X + 110 * mm
    col4_x = MARGIN_X + 130 * mm
    
    c.drawString(col1_x, y, "CONCEPTO")
    c.drawString(col2_x, y, "PRECIO SIN IVA")
    c.drawString(col3_x, y, "TIPO IVA")
    c.drawString(col4_x, y, "PRECIO CON IVA")
    
    y -= 4*mm
    c.line(MARGIN_X, y, width - MARGIN_X, y)
    y -= 4*mm
    
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
        
        y -= 2*mm
        if idx < len(datos_factura['conceptos']) - 1:
            c.line(MARGIN_X, y, width - MARGIN_X, y)
            y -= 4*mm
        else:
            y -= 2*mm
    
    # Totales
    y -= 6*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, "Importes")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_X, y, f"Base imponible: {eur(datos_factura['base_imponible'])}")
    y -= 5*mm
    c.drawString(MARGIN_X, y, f"IVA total: {eur(datos_factura['iva'])}")
    y -= 5*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, y, f"TOTAL: {eur(datos_factura['total'])}")
    
    # Pie
    y -= 12*mm
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN_X, y, "Factura")
    
    c.showPage()
    c.save()
    
    return nombre_pdf
