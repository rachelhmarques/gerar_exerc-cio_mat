import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
import re
from datetime import datetime
from io import BytesIO

st.title("Conversor de Extrato Bancário (PDF via OCR para OFX)")

uploaded_file = st.file_uploader("Carregue o arquivo PDF do extrato", type="pdf")

if uploaded_file is not None:
    # Converte PDF para imagens
    images = convert_from_bytes(uploaded_file.read())

    texto_total = ""
    for img in images:
        texto = pytesseract.image_to_string(img, lang='por')  # OCR com idioma português
        texto_total += texto + "\n"

    transacoes = []

    # Obtém o ano do extrato
    match = re.search(r'Período do extrato\s+(\d{2})\s*/\s*(\d{4})', texto_total)
    ano_extrato = match.group(2) if match else '2025'

    # Regex geral: data, documento, valor e D/C
    regex = re.compile(r"(\d{2}/\d{2}/\d{4}).*?(\d{3}(?:\.\d+)+).*?([\d\.]+,\d{2})\s+([DC])", re.DOTALL)

    for m in regex.finditer(texto_total):
        data_br, doc_num, valor_str, tipo = m.groups()
        data_fmt = datetime.strptime(data_br, "%d/%m/%Y").strftime("%Y%m%d")
        valor_fmt = valor_str.replace('.', '').replace(',', '.')
        valor_fmt = f"-{valor_fmt}" if tipo == 'D' else valor_fmt
        tipo_transacao = "DEBIT" if tipo == 'D' else "CREDIT"

        transacoes.append({
            "Data": data_fmt,
            "Documento": doc_num[-6:],
            "Valor": valor_fmt,
            "Tipo": tipo_transacao,
            "Descricao": f"Movimentação {data_br}",
            "FITID": f"{data_fmt}{doc_num[-3:]}"
        })

    # === GERAÇÃO DO ARQUIVO OFX ===
    ofx_conteudo = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
 <SONRS>
  <STATUS>
   <CODE>0</CODE>
   <SEVERITY>INFO</SEVERITY>
  </STATUS>
  <DTSERVER>20250602
  <LANGUAGE>POR
  <DTACCTUP>20250602
  <FI>
   <ORG>Banco do Brasil S/A
   <FID>001
  </FI>
 </SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
 <STMTTRNRS>
  <TRNUID>0
   <STATUS>
    <CODE>0
    <SEVERITY>INFO
   </STATUS>
   <STMTRS>
    <CURDEF>BRL
    <BANKACCTFROM>
     <BANKID>001
     <ACCTID>29483-7 
     <ACCTTYPE>CHECKING
    </BANKACCTFROM>
    <BANKTRANLIST>
     <DTSTART>20250101
     <DTEND>20250131
"""

    for t in transacoes:
        ofx_conteudo += f"""<STMTTRN>
  <TRNTYPE>{t['Tipo']}
  <DTPOSTED>{t['Data']}
  <TRNAMT>{t['Valor']}
  <FITID>{t['FITID']}
  <CHECKNUM>{t['Documento']}
  <MEMO>{t['Descricao']}
</STMTTRN>
"""

    ofx_conteudo += """</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

    st.subheader("Transações encontradas")
    st.table(transacoes)

    st.download_button(
        label="Baixar arquivo OFX",
        data=ofx_conteudo,
        file_name="extrato.ofx",
        mime="application/ofx"
    )

    st.success("Conversão concluída com sucesso!")
