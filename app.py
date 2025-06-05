import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime
import os
from io import StringIO

st.title("Conversor de Extrato Bancário (PDF para OFX)")

# === Upload do PDF ===
uploaded_file = st.file_uploader("Carregue o arquivo PDF do extrato", type="pdf")

if uploaded_file is not None:
    # === EXTRAÇÃO DE DADOS DO PDF ===
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    linhas = []
    for pagina in doc:
        linhas.extend(pagina.get_text().splitlines())

    transacoes = []
    i = 0
    while i < len(linhas) - 4:
        try:
            datetime.strptime(linhas[i].strip(), "%d/%m/%Y")
            data_br = linhas[i].strip()
            tipo_linha = linhas[i + 2].strip()
            doc_linha = linhas[i + 3].strip()
            valor_linha = linhas[i + 4].strip()

            match_valor = re.match(r"([\d\.]+,\d{2})\s+([DC])", valor_linha)
            if match_valor:
                valor, tipo = match_valor.groups()
                data_fmt = datetime.strptime(data_br, "%d/%m/%Y").strftime("%Y%m%d")
                valor_fmt = valor.replace(".", "").replace(",", ".")
                valor_fmt = f"-{valor_fmt}" if tipo == 'D' else valor_fmt
                tipo_transacao = "DEBIT" if tipo == 'D' else "CREDIT"

                doc_num = re.sub(r"[^\d]", "", doc_linha)[-6:]

                nome_linha = linhas[i + 5].strip() if (i + 5) < len(linhas) else ""
                nome_valido = nome_linha and not re.search(r"\d+,\d{2}", nome_linha)
                descricao = nome_linha if nome_valido else tipo_linha

                transacoes.append({
                    "Data": data_fmt,
                    "Documento": doc_num,
                    "Valor": valor_fmt,
                    "Tipo": tipo_transacao,
                    "Descricao": descricao,
                    "FITID": f"{data_fmt}{doc_num[-3:]}"
                })

                i += 6 if nome_valido else 5
            else:
                i += 1
        except ValueError:
            i += 1

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
     <DTSTART>20250501 
     <DTEND>20250531 
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

    # Mostra prévia das transações
    st.subheader("Transações encontradas")
    st.table(transacoes[:10])  # Mostra apenas as primeiras 10 para não sobrecarregar a tela

    # Cria um botão de download
    st.download_button(
        label="Baixar arquivo OFX",
        data=ofx_conteudo,
        file_name="extrato.ofx",
        mime="application/ofx"
    )

    st.success("Conversão concluída com sucesso!")