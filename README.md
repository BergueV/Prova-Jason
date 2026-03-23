# Prova Técnica NASAJON – README

## Como rodar

### Pré-requisitos
- Python 3.10 ou superior instalado
- Instalar dependências:

```bash
pip install requests
```

---

### Passo a passo

**1. Preencha seus dados no `main.py`**



**2. Rode o script pela primeira vez (cadastro)**

```bash
python main.py
```

O script vai se cadastrar no Supabase e avisar para você confirmar o e-mail.
Vá ao seu e-mail, clique no link de confirmação da NASAJON/Supabase.

---

**3. Rode novamente (execução completa)**

```bash
python main.py
```

Desta vez o script vai:
- Fazer login e obter o ACCESS_TOKEN
- Baixar todos os municípios do IBGE
- Processar o `input.csv` com matching inteligente (trata erros de digitação e acentos)
- Gerar o `resultado.csv`
- Calcular as estatísticas
- Enviar para a API de correção e mostrar sua nota (score) no terminal

---

## Decisões técnicas

- **Matching**: normalização (remoção de acentos + lowercase) + busca difusa via `difflib.get_close_matches` com threshold 0.75. Isso resolve casos como "Belo Horzionte" → "Belo Horizonte" e "Curitba" → "Curitiba".
- **AMBIGUO**: marcado quando há mais de um município IBGE com o mesmo nome normalizado (ex: mesmo nome em estados diferentes).
- **NAO_ENCONTRADO**: quando nenhuma correspondência supera o threshold.
- **Sem bibliotecas externas pesadas**: apenas `requests` + módulos padrão do Python.
