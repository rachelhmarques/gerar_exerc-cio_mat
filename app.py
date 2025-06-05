import streamlit as st
import fitz  # PyMuPDF
import re
from datetime import datetime

st.title("Conversor de Extrato Bancário (PDF para OFX)")

uploaded_file = st.file_uploader("Carregue o arquivo PDF do extrato", type="pdf")

if uploaded_file is not None:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    linhas = []
    for pagina in doc:
        linhas.extend(pagina.get_text().splitlines())

    transacoes = []

    # Obtém o ano do extrato
    ano_extrato = None
    for linha in linhas:
        match = re.search(r'Período do extrato\s+(\d{2}) / (\d{4})', linha)
        if match:
            mes_extrato, ano_extrato = match.groups()
            break
    if not ano_extrato:
        ano_extrato = '2025'  # fallback

    for i in range(len(linhas)):
        linha = linhas[i].strip()

        # Procura valor com D/C
        match_valor = re.search(r"([\d\.]+,\d{2})\s+([DC])", linha)
        if match_valor:
            valor_str, tipo = match_valor.groups()
            valor_fmt = valor_str.replace('.', '').replace(',', '.')
            valor_fmt = f"-{valor_fmt}" if tipo == 'D' else valor_fmt
            tipo_transacao = "DEBIT" if tipo == 'D' else "CREDIT"

            # Busca data: nesta linha ou até 2 linhas acima
            data_br = None
            for j in range(i, max(i - 3, -1), -1):
                linha_data = linhas[j]
                match_data = re.search(r"(\d{2}/\d{2}/\d{4})", linha_data)
                match_data_parcial = re.search(r"(\d{2}/\d{2})(?!/)", linha_data)
                if match_data:
                    data_br = match_data.group(1)
                    break
                elif match_data_parcial:
                    data_br = f"{match_data_parcial.group(1)}/{ano_extrato}"
                    break

            if data_br:
                data_fmt = datetime.strptime(data_br, "%d/%m/%Y").strftime("%Y%m%d")
            else:
                data_fmt = "00000000"  # placeholder se não achar

            # Documento: número longo
            match_doc = re.search(r"(\d{3}(?:\.\d+)+)", linha)
            if not match_doc:
                match_doc = re.search(r"\d{2,}", linha)
            doc_num = match_doc.group(0) if match_doc else "000000"

            # Descrição: linha anterior ou próxima, se não for valor
            descricao = ""
            if i + 1 < len(linhas):
                prox_linha = linhas[i + 1].strip()
                if not re.search(r"([\d\.]+,\d{2})\s+[DC]", prox_linha):
                    descricao = prox_linha
            if not descricao and i > 0:
                ant_linha = linhas[i - 1].strip()
                if not re.search(r"([\d\.]+,\d{2})\s+[DC]", ant_linha):
                    descricao = ant_linha

            transacoes.append({
                "Data": data_fmt,
                "Documento": doc_num[-6:],
                "Valor": valor_fmt,
                "Tipo": tipo_transacao,
                "Descricao": descricao if descricao else linha,
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
