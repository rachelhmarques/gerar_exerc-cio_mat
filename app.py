import streamlit as st
from fpdf import FPDF
from random import randint

# Função para desenhar a régua
def desenhar_regua(pdf, font_size, font_color):
    pdf.set_text_color(*font_color)
    pdf.set_font("Arial", size=font_size)
    regua = " · ".join(str(i) for i in range(0, 21))
    pdf.multi_cell(0, 8, f"Régua de Soma:\n{regua}", align="C")
    pdf.ln(5)

# Função para gerar exercícios
def gerar_exercicios(valor_soma, quantidade, simples=False, limite=None):
    exercicios = []
    for _ in range(quantidade):
        if limite:
            a = randint(1, limite)
        elif simples:
            a = randint(1, 20)
        else:
            a = randint(100, 999)
        b = valor_soma
        exercicios.append(f"{a} + {b} = _________")
    return exercicios

# Função principal para gerar o PDF
def gerar_pdf(font_size, num_colunas, quantidade, simples, somas, font_color):
    if quantidade > 20 or font_size > 14:
        num_colunas = 2  # ajuste automático

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False, margin=15)

    for soma in somas:
        pdf.add_page()
        pdf.set_text_color(*font_color)
        pdf.set_font("Arial", "B", font_size + 4)
        pdf.cell(0, 10, f"Exercícios de Soma {soma}", align="C")
        pdf.ln(10)
        
        desenhar_regua(pdf, font_size, font_color)
        
        exercicios = gerar_exercicios(soma, quantidade, simples=simples)

        col_width = (pdf.w - 20) / num_colunas
        row_height = font_size + 2
        
        pdf.set_font("Arial", size=font_size)
        pdf.set_text_color(*font_color)
        x_positions = [10 + i * col_width for i in range(num_colunas)]
        y_start = pdf.get_y() + 5
        
        linhas_por_coluna = len(exercicios) // num_colunas + (len(exercicios) % num_colunas > 0)
        
        for col in range(num_colunas):
            x = x_positions[col]
            y = y_start
            for i in range(linhas_por_coluna):
                idx = col * linhas_por_coluna + i
                if idx >= len(exercicios):
                    break
                pdf.set_xy(x, y)
                pdf.multi_cell(col_width - 5, row_height, exercicios[idx])
                y += row_height + 2

    return pdf.output(dest='S').encode('latin1')  # retorna bytes do PDF

# --- Streamlit UI ---

st.title("Gerador de Exercícios de Soma")

font_size = st.slider("Tamanho da Fonte", min_value=8, max_value=20, value=12)
num_colunas = st.slider("Número de Colunas", min_value=1, max_value=3, value=2)
quantidade = st.slider("Quantidade de Exercícios por Soma", min_value=5, max_value=50, value=10)
simples = st.checkbox("Somas Simples?")
soma_min = st.number_input("Soma Mínima", min_value=1, max_value=50, value=1)
soma_max = st.number_input("Soma Máxima", min_value=1, max_value=50, value=3)

if soma_max < soma_min:
    st.error("Soma máxima deve ser maior ou igual à mínima.")
    st.stop()

# Escolha da cor da fonte - usando seletor de cor do Streamlit
cor_hex = st.color_picker("Escolha a cor da fonte", "#000000")

# Converter HEX para RGB (0-255)
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

font_color = hex_to_rgb(cor_hex)

somas = list(range(soma_min, soma_max + 1))

if st.button("Gerar PDF"):
    pdf_bytes = gerar_pdf(font_size, num_colunas, quantidade, simples, somas, font_color)
    st.success("✅ PDF gerado com sucesso!")
    st.download_button(
        label="Baixar PDF",
        data=pdf_bytes,
        file_name="exercicios_somas_custom.pdf",
        mime="application/pdf"
    )
