from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    """
    Clase para generar informes en PDF con encabezado, pie de página y tablas.
    """
    def header(self):
        """Define el encabezado del PDF."""
        self.set_font('Arial', 'B', 12)
        # Título del reporte (se establece dinámicamente)
        self.cell(0, 10, self.title, 0, 1, 'C')
        # Fecha de generación
        self.set_font('Arial', '', 8)
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        self.cell(0, 10, f'Generado el: {fecha_gen}', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        """Define el pie de página del PDF."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        # Número de página
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def create_table_report(self, table_data, headers, column_widths, report_title='Informe'):
        """
        Crea una tabla en el PDF a partir de los datos proporcionados.

        :param table_data: Una lista de listas/tuplas con los datos de las filas.
        :param headers: Una lista con los nombres de las columnas.
        :param column_widths: Una lista con los anchos de cada columna.
        :param report_title: El título principal del informe.
        """
        self.set_title(report_title)
        self.set_author('Bot de Gestión de Obra')
        self.alias_nb_pages()
        self.add_page(orientation='L') # Orientación horizontal para más espacio

        # --- Cabecera de la tabla ---
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(200, 220, 255)  # Color de fondo azul claro
        for i, header in enumerate(headers):
            self.cell(column_widths[i], 7, header, 1, 0, 'C', 1)
        self.ln()

        # --- Filas de datos ---
        self.set_font('Arial', '', 9)
        fill = False
        for row in table_data:
            self.set_fill_color(240, 240, 240) # Color de fondo gris claro para filas alternas
            for i, datum in enumerate(row):
                # Usamos multi_cell para manejar texto largo que necesita saltos de línea
                self.multi_cell(column_widths[i], 6, str(datum), border=1, align='L', fill=fill)
            self.ln()
            fill = not fill # Alternar color de fondo

        # Devuelve el contenido del PDF como bytes
        return self.output(dest='S').encode('latin-1')