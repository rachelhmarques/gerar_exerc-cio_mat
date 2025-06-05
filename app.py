import streamlit as st
import pdfplumber
import re
from datetime import datetime

st.title("Conversor de Extrato Bancário (PDF para OFX) - pdfplumber")

uploaded_file = st.file_uploader("Carregue o arquivo PDF do extrato", type="pdf")

if uploaded_file is not None:
    transacoes = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    # Evita linhas nulas
                    if not row or len(row) < 6:
                        continue

                    # Exemplo de colunas: Dt. movimento | Ag. origem | Lote | Histórico | Documento | Valor | Saldo
                    data_raw = row[0]
                    historico = row[3]
                    documento = row[4]
                    valor_raw = row[5]
                    
                    # Ajuste conforme estrutura real das colunas

                    # Verifica se a data está no formato esperado
                    match_data = re.match(r"(\d{2}/\d{2}/\d{4})", data_raw)
                    if not match_data:
                        continue

                    data_br = match_data.group(1)
                    data_fmt = datetime.strptime(data_br, "%d/%m/%Y").strftime("%Y%m%d")

                    # Verifica valor e tipo (D ou C)
                    match_valor = re.search(r"([\d\.]+,\d{2})\s*([DC])", valor_raw)
                    if not match_valor:
                        continue

                    valor_str, tipo = match_valor.groups()
                    valor_fmt = valor_str.replace('.', '').replace(',', '.')
                    valor_fmt = f"-{valor_fmt}" if tipo == 'D' else valor_fmt
                    tipo_transacao = "DEBIT" if tipo == 'D' else "CREDIT"

                    transacoes.append({
                        "Data": data_fmt,
                        "Documento": documento[-6:],
                        "Valor": valor_fmt,
                        "Tipo": tipo_transacao,
                        "Descricao": historico,
                        "FITID": f"{data_fmt}{documento[-3:]}"
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
